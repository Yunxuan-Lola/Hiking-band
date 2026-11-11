import pathlib
import struct
import sys
import unittest
import pickle
import tempfile
import types
import os
import csv
from unittest import mock

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'RPi'))
from features import ActivityFeatureExtractor
from stream_protocol import decode, PACKET
from train_public import windows, feature_vector, feature_matrix
from activity_rec import ActivityRecognition
from sklearn.ensemble import RandomForestClassifier
import hike
import db


class PipelineTests(unittest.TestCase):
    def test_wire_packet_units_and_endianness(self):
        sample = decode(struct.pack('<BHIhhhH', 0x11, 65535, 1234, -1024, 0, 1000, 2))
        self.assertEqual(PACKET.size, 15)
        self.assertEqual((sample.sequence, sample.timestamp_ms, sample.dropped), (65535, 1234, 2))
        self.assertEqual((sample.x_g, sample.y_g, sample.z_g), (-1.024, 0., 1.))
        with self.assertRaises(ValueError): decode(b'\x11')
        with self.assertRaises(ValueError): decode(bytes(15))

    def test_batch_features_match_streaming_features(self):
        samples = np.random.default_rng(42).normal(size=(4, 50, 3))
        expected = np.stack([feature_vector(window) for window in samples])
        np.testing.assert_allclose(feature_matrix(samples), expected, rtol=1e-12, atol=1e-12)

    def test_frequency_is_hz_and_drops_gravity_dc(self):
        t = np.arange(50) / 25
        f = ActivityFeatureExtractor(50, 25, 25)
        for x in np.sin(2*np.pi*2*t) + 1:
            f.add_sample(x, 0, 0)
        self.assertAlmostEqual(f.extract_features()[11], 2.)

    def test_gaps_do_not_cross_windows(self):
        t = np.r_[np.arange(30)/25, 10 + np.arange(30)/25]
        samples = np.column_stack((t, np.ones((60, 3))))
        self.assertEqual(list(windows(samples)), [])
        t = np.arange(100)/100
        self.assertEqual(list(windows(np.column_stack((t, np.ones((100, 3)))))), [])

    def test_inference_hop_and_gap_reset(self):
        model = RandomForestClassifier(n_estimators=2, random_state=2)
        model.fit(np.vstack([np.zeros(48), np.ones(48)]), ['idle', 'walking'])
        with tempfile.NamedTemporaryFile() as f:
            pickle.dump({'feature_version': 2, 'sample_rate': 25, 'window': 50, 'hop': 25, 'model': model}, f)
            f.flush()
            recognizer = ActivityRecognition(f.name)
            self.assertTrue(recognizer.initialize())
            for _ in range(49): recognizer.add_imu_sample(0, 0, 0)
            self.assertEqual(sum(recognizer.activity_counts.values()), 0)
            recognizer.add_imu_sample(0, 0, 0)
            self.assertEqual(sum(recognizer.activity_counts.values()), 1)
            for _ in range(24): recognizer.add_imu_sample(0, 0, 0)
            self.assertEqual(sum(recognizer.activity_counts.values()), 1)
            recognizer.add_imu_sample(0, 0, 0)
            self.assertEqual(sum(recognizer.activity_counts.values()), 2)
            recognizer.reset_window()
            self.assertEqual(sum(recognizer.activity_counts.values()), 2)
            for _ in range(49): recognizer.add_imu_sample(0, 0, 0)
            self.assertEqual(sum(recognizer.activity_counts.values()), 2)

    def test_ble_sequence_gap_discards_partial_window(self):
        fake_bluepy = types.ModuleType('bluepy')
        fake_bluepy.btle = types.SimpleNamespace(DefaultDelegate=object, BTLEException=Exception)
        with mock.patch.dict(sys.modules, {'bluepy': fake_bluepy}):
            import bt
            recognizer = mock.Mock()
            bt.set_activity_recognition(recognizer)
            delegate = bt.NotificationDelegate(mock.Mock(), mock.Mock())
            delegate.record = mock.Mock()
            delegate.handleNotification(1, struct.pack('<BHIhhhH', 0x11, 7, 1000, 0, 0, 1000, 0))
            delegate.handleNotification(1, struct.pack('<BHIhhhH', 0x11, 9, 1080, 0, 0, 1000, 0))
            delegate.inference_queue.join()
            recognizer.reset_window.assert_called_once()
            self.assertEqual(recognizer.add_imu_sample.call_count, 2)
            delegate.close()

    def test_legacy_json_is_not_treated_as_motion_or_steps(self):
        fake_bluepy = types.ModuleType('bluepy')
        fake_bluepy.btle = types.SimpleNamespace(DefaultDelegate=object, BTLEException=Exception)
        with mock.patch.dict(sys.modules, {'bluepy': fake_bluepy}):
            import bt
            recognizer = mock.Mock()
            bt.set_activity_recognition(recognizer)
            sessions = bt.HubBluetooth.messages_to_sessions(['{"type":"imu","ax":1}', '42'])
            self.assertEqual([s.steps for s in sessions], [42])
            recognizer.add_imu_sample.assert_not_called()

    def test_recording_queue_flushes_on_close(self):
        fake_bluepy = types.ModuleType('bluepy')
        fake_bluepy.btle = types.SimpleNamespace(DefaultDelegate=object, BTLEException=Exception)
        with mock.patch.dict(sys.modules, {'bluepy': fake_bluepy}):
            import bt
            delegate = bt.NotificationDelegate(mock.Mock(), mock.Mock())
            sample = decode(struct.pack('<BHIhhhH', 0x11, 1, 40, -500, 0, 1000, 0))
            with tempfile.TemporaryDirectory() as temp:
                previous = os.getcwd()
                try:
                    os.chdir(temp)
                    delegate.record(sample)
                    delegate.close()
                    path = next(pathlib.Path('recordings').glob('*.csv'))
                    with path.open(newline='') as source:
                        rows = list(csv.DictReader(source))
                    self.assertEqual(rows[0]['sequence'], '1')
                    self.assertEqual(rows[0]['x_g'], '-0.5')
                    self.assertTrue(rows[0]['received_at_utc'].endswith('+00:00'))
                    self.assertEqual(rows[0]['gap_before'], '')
                finally:
                    os.chdir(previous)

    def test_recorded_gap_is_marked_for_replay(self):
        fake_bluepy = types.ModuleType('bluepy')
        fake_bluepy.btle = types.SimpleNamespace(DefaultDelegate=object, BTLEException=Exception)
        with mock.patch.dict(sys.modules, {'bluepy': fake_bluepy}):
            import bt
            delegate = bt.NotificationDelegate(mock.Mock(), mock.Mock())
            with tempfile.TemporaryDirectory() as temp:
                previous = os.getcwd()
                try:
                    os.chdir(temp)
                    for sequence, timestamp in [(1, 40), (3, 120)]:
                        delegate.handleNotification(1, struct.pack(
                            '<BHIhhhH', 0x11, sequence, timestamp, 0, 0, 1000, 0))
                    delegate.close()
                    path = next(pathlib.Path('recordings').glob('*.csv'))
                    with path.open(newline='') as source:
                        rows = list(csv.DictReader(source))
                    self.assertEqual(rows[1]['gap_before'], 'sequence,watch_time')
                finally:
                    os.chdir(previous)

    def test_database_preserves_activity_fields(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(db, 'DB_FILE_NAME', str(pathlib.Path(temp) / 'sessions.db')):
            database = db.HubDatabase()
            session = hike.HikeSession()
            session.id = 'test-session'; session.km = 1.2; session.steps = 1500; session.kcal = 100
            session.activity_mode = 'walking'; session.activity_distribution = {'walking': .75, 'idle': .25}
            database.save(session, 'test-user')
            restored = database.get_sessions('test-user')[0]
            self.assertEqual(restored.activity_mode, 'walking')
            self.assertEqual(restored.activity_distribution, {'walking': .75, 'idle': .25})
            round_trip = hike.from_list(hike.to_list(session))
            self.assertEqual(round_trip.activity_mode, 'walking')
            self.assertEqual(round_trip.activity_distribution, session.activity_distribution)

    def test_sessions_are_newest_first_and_state_is_independent(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(db, 'DB_FILE_NAME', str(pathlib.Path(temp) / 'sessions.db')):
            database = db.HubDatabase()
            for session_id in ['2025-01-01 10:00:00', '2025-01-02 10:00:00']:
                session = hike.HikeSession()
                session.id = session_id
                session.steps = 10
                database.save(session, 'user')
            self.assertEqual([s.id for s in database.get_sessions('user')],
                             ['2025-01-02 10:00:00', '2025-01-01 10:00:00'])
            first, second = hike.HikeSession(), hike.HikeSession()
            first.activity_distribution['walking'] = 1.0
            self.assertEqual(second.activity_distribution, {})


if __name__ == '__main__': unittest.main()
