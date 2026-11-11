import time
from bluepy import btle
import hike
from datetime import datetime, timezone
import db
import os
import logging
import csv
import queue
import threading
from pathlib import Path
from stream_protocol import decode, VERSION_TYPE

WATCH_BT_MAC = os.environ.get('HIKING_WATCH_MAC', '94:B5:55:C8:E9:3E')

activity_recognition = None


def set_activity_recognition(ar):
    global activity_recognition
    activity_recognition = ar


class HubBluetooth:
    """Handles Bluetooth pairing and synchronization with the Watch. """

    connected = False
    peripheral = None

    def wait_for_connection(self):
        """Synchronous function continuously trying to connect to the Watch by 2 sec intervals.
        If a connection has been made, it sends the watch a `c` ASCII character as a confirmation.
        """
        if not self.connected:
            while True:
                print("Waiting for connection...")
                try:
                    self.peripheral = btle.Peripheral(WATCH_BT_MAC, iface=0)
                    service = self.peripheral.getServiceByUUID('6e400001-b5a3-f393-e0a9-e50e24dcca9e')
                    self.tx = service.getCharacteristics('6e400003-b5a3-f393-e0a9-e50e24dcca9e')[0]
                    self.rx = service.getCharacteristics('6e400002-b5a3-f393-e0a9-e50e24dcca9e')[0]
                    cccd = self.tx.getDescriptors(forUUID=0x2902)[0]
                    cccd.write(b'\x01\x00', withResponse=True)
                    self.connected = True
                    print("Connected to Watch!")
                    self.send_message("c")
                    break
                except btle.BTLEException as e:
                    print(f"Connection failed: {e}. Retrying in 2 seconds...")
                    time.sleep(2)
            print("Hub: Established Bluetooth connection with Watch!")
        else:
            print("WARNING Hub: already connected via Bluetooth.")

    def send_message(self, message):
        """Sends a message to the Watch over BLE."""
        if self.connected:
            try:
                self.rx.write(message.encode(), withResponse=True)
            except btle.BTLEException as e:
                print(f"Error sending message: {e}")

    def synchronize(self, callback):
        """Continuously tries to receive data from an established connection with the Watch."""
        print("Synchronizing with watch...")
        delegate = None
        while True:
            try:
                delegate = NotificationDelegate(callback, self)
                self.peripheral.setDelegate(delegate)
                while True:
                    self.peripheral.waitForNotifications(1.0)
            except KeyboardInterrupt:
                self.peripheral.disconnect()
                print("Shutting down the receiver.")
                raise
            except btle.BTLEException as e:
                print(f"Lost connection with the watch: {e}")
                self.connected = False
                self.peripheral.disconnect()
                break
            finally:
                if delegate:
                    delegate.close()
                if activity_recognition:
                    activity_recognition.reset_window()

    @staticmethod
    def messages_to_sessions(messages):
        sessions = []
        for msg in messages:
            if not msg:
                continue
            try:
                session = HubBluetooth.mtos(msg.encode())
                sessions.append(session)
            except (ValueError, UnicodeError):
                logging.warning('Ignoring invalid step summary: %r', msg)
        return sessions

    @staticmethod
    def mtos(message: bytes) -> hike.HikeSession:
        m = message.decode('utf-8')
        steps = int(m)
        hs = hike.HikeSession()
        hs.id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hs.steps = steps
        hs.km = round(steps * 0.0008, 3)
        hs.calc_kcal()
        return hs


class NotificationDelegate(btle.DefaultDelegate):
    """Handles incoming BLE notifications from the Watch."""

    def __init__(self, callback, hubbt):
        super().__init__()
        self.callback = callback
        self.hubbt = hubbt
        self.last_sequence = None
        self.last_timestamp = None
        self.last_watch_dropped = None
        self.record_queue = queue.Queue(maxsize=512)
        self.record_thread = None
        self.record_dropped = 0
        self.record_failed = threading.Event()
        self.inference_queue = queue.Queue(maxsize=256)
        self.pending_reset = None
        self.inference_dropped = 0
        self.inference_thread = threading.Thread(target=self._inference_worker, daemon=True)
        self.inference_thread.start()

    def _inference_worker(self):
        while True:
            item = self.inference_queue.get()
            try:
                if item is None:
                    return
                sample, reset_kind = item
                if activity_recognition:
                    if reset_kind == 'session':
                        activity_recognition.reset()
                    elif reset_kind == 'gap':
                        activity_recognition.reset_window()
                    activity_recognition.add_imu_sample(sample.x_g, sample.y_g, sample.z_g)
            except Exception:
                logging.exception('Activity inference failed')
            finally:
                self.inference_queue.task_done()

    def _record_worker(self, path):
        try:
            with path.open('w', newline='') as output:
                writer = csv.writer(output)
                writer.writerow(['sequence', 'watch_time_ms', 'x_g', 'y_g', 'z_g',
                                 'watch_dropped', 'received_at_utc', 'gap_before'])
                count = 0
                while True:
                    item = self.record_queue.get()
                    try:
                        if item is None:
                            break
                        sample, received_at, gap_before = item
                        writer.writerow([sample.sequence, sample.timestamp_ms, sample.x_g,
                                         sample.y_g, sample.z_g, sample.dropped,
                                         received_at, gap_before])
                        count += 1
                        if count % 25 == 0:
                            output.flush()
                    finally:
                        self.record_queue.task_done()
        except OSError:
            self.record_failed.set()
            logging.exception('CSV recording failed')

    def close(self):
        try:
            self.inference_queue.put(None, timeout=2)
        except queue.Full:
            logging.error('Inference worker did not drain on shutdown')
        self.inference_thread.join(timeout=5)
        if self.inference_dropped:
            logging.warning('Inference queue dropped %d samples', self.inference_dropped)
        if self.record_thread:
            try:
                if not self.record_failed.is_set():
                    self.record_queue.put(None, timeout=2)
            except queue.Full:
                logging.error('CSV writer did not drain on shutdown')
            self.record_thread.join(timeout=5)
            if self.record_dropped:
                logging.warning('CSV writer queue dropped %d samples', self.record_dropped)

    def record(self, sample, gap_before=''):
        if self.record_failed.is_set():
            self.record_dropped += 1
            return
        if self.record_thread is None:
            Path('recordings').mkdir(exist_ok=True)
            path = Path('recordings') / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.csv')
            self.record_thread = threading.Thread(target=self._record_worker, args=(path,), daemon=True)
            self.record_thread.start()
        try:
            received_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
            self.record_queue.put_nowait((sample, received_at, gap_before))
        except queue.Full:
            self.record_dropped += 1

    def handleNotification(self, cHandle, data):
        try:
            if data and data[0] == VERSION_TYPE:
                sample = decode(data)
                reset_kind = self.pending_reset
                gap_reasons = []
                if self.last_sequence is not None:
                    if sample.sequence != (self.last_sequence + 1) % 65536:
                        gap_reasons.append('sequence')
                    if (sample.timestamp_ms - self.last_timestamp) % (2 ** 32) >= 80:
                        gap_reasons.append('watch_time')
                    if sample.dropped != self.last_watch_dropped:
                        gap_reasons.append('watch_dropped')
                if gap_reasons:
                    logging.warning('IMU packet gap: previous=%s current=%s', self.last_sequence, sample.sequence)
                    if sample.sequence == 0 and self.last_sequence != 65535:
                        reset_kind = 'session'
                    elif reset_kind != 'session':
                        reset_kind = 'gap'
                self.record(sample, ','.join(gap_reasons))
                self.last_sequence = sample.sequence
                self.last_timestamp = sample.timestamp_ms
                self.last_watch_dropped = sample.dropped
                try:
                    self.inference_queue.put_nowait((sample, reset_kind))
                    self.pending_reset = None
                except queue.Full:
                    self.inference_dropped += 1
                    self.pending_reset = 'session' if reset_kind == 'session' else 'gap'
                return
            data_str = data.decode("utf-8")
            messages = data_str.split("\n")
            sessions = HubBluetooth.messages_to_sessions(messages)
            if sessions:
                self.inference_queue.join()
                for h in sessions:
                    print(f"Session: {hike.to_list(h)}")
                self.callback(sessions, db.user0)
                self.hubbt.send_message("r")
        except Exception as e:
            print(f"Error processing data: {e}")
