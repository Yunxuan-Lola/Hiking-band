"""Export one resampled SELFBack window for offline pipeline smoke checks."""
import argparse
import csv
from train_public import rows_from_archive, windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive')
    parser.add_argument('output')
    parser.add_argument('--subject', default='007')
    parser.add_argument('--label', choices=('idle', 'walking', 'climbing', 'running'), default='walking')
    args = parser.parse_args()
    for subject, label, samples in rows_from_archive(args.archive, selected_subject=args.subject):
        if subject != args.subject or label != args.label:
            continue
        first = next(windows(samples), None)
        if first is None:
            continue
        with open(args.output, 'w', newline='') as destination:
            writer = csv.writer(destination)
            writer.writerow(['sequence', 'watch_time_ms', 'x_g', 'y_g', 'z_g',
                             'watch_dropped', 'received_at_utc', 'gap_before'])
            for seq, (x, y, z) in enumerate(first):
                writer.writerow([seq, seq * 40, x, y, z, 0, '', ''])
        print(f'Exported subject={subject} label={label}; public data is not T-Watch data')
        return
    raise SystemExit('No matching data found')


if __name__ == '__main__': main()
