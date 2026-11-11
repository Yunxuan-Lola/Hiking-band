"""Replay a recorded BLE CSV through the deployed activity model."""
import argparse
import csv
import json
from activity_rec import ActivityRecognition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file')
    parser.add_argument('--model')
    args = parser.parse_args()
    recognizer = ActivityRecognition(args.model, verbose=False)
    if not recognizer.initialize():
        raise SystemExit('Unable to load a compatible trusted model')
    last_seq = last_time = last_dropped = None
    with open(args.csv_file, newline='') as source:
        for row in csv.DictReader(source):
            seq = int(row['sequence'])
            watch_time = int(row['watch_time_ms'])
            dropped = int(row['watch_dropped'])
            gap = row.get('gap_before') or ''
            if last_seq is not None and (seq != (last_seq + 1) % 65536 or
                    (watch_time - last_time) % (2 ** 32) >= 80 or
                    dropped != last_dropped):
                gap = gap or 'detected'
            if gap:
                if seq == 0 and last_seq not in (None, 65535):
                    recognizer.reset()
                else:
                    recognizer.reset_window()
            last_seq = seq
            last_time = watch_time
            last_dropped = dropped
            before = recognizer.last_prediction
            recognizer.add_imu_sample(float(row['x_g']), float(row['y_g']), float(row['z_g']))
            if recognizer.last_prediction is not before:
                print(json.dumps({'watch_time_ms': watch_time, **recognizer.last_prediction}))


if __name__ == '__main__': main()
