"""Train an activity model from the public SELFBack wrist50 ZIP archive."""
import argparse
import csv
import io
import json
import math
import pickle
import zipfile
from datetime import datetime
from pathlib import PurePosixPath

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from scipy.signal import butter, sosfiltfilt

from features import ActivityFeatureExtractor

LABELS = {'walking': 'walking', 'jogging': 'running', 'standing': 'idle',
          'sitting': 'idle', 'upstairs': 'climbing'}
RATE, WINDOW, HOP, FEATURE_VERSION = 25, 50, 25, 2


def rows_from_archive(archive, max_subjects=0, selected_subject=None):
    with zipfile.ZipFile(archive) as z:
        subjects = sorted({PurePosixPath(n).stem for n in z.namelist()
                           if '/raw/6_class/wrist50/' in n and PurePosixPath(n).suffix == '.csv'})
        allowed = set(subjects[:max_subjects]) if max_subjects else set(subjects)
        if selected_subject is not None:
            allowed &= {selected_subject}
        for name in sorted(z.namelist()):
            p = PurePosixPath(name)
            if '/raw/6_class/wrist50/' not in name or p.suffix != '.csv' or p.parent.name not in LABELS or p.stem not in allowed:
                continue
            with z.open(name) as raw:
                rows = csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8-sig'))
                samples = []
                origin = None
                for row in rows:
                    try:
                        stamp = datetime.fromisoformat(row['time'])
                        if origin is None:
                            origin = stamp
                        ts = (stamp - origin).total_seconds()
                        xyz = [float(row[k]) for k in ('x', 'y', 'z')]
                        if all(map(math.isfinite, xyz)):
                            samples.append((ts, *xyz))
                    except (ValueError, KeyError):
                        continue
            if samples:
                yield p.stem, LABELS[p.parent.name], np.asarray(samples, dtype=float)


def windows(samples):
    # Split gaps, duplicates and time reversal before interpolation.
    edges = np.flatnonzero((np.diff(samples[:, 0]) <= 0) | (np.diff(samples[:, 0]) > .2)) + 1
    for segment in np.split(samples, edges):
        if len(segment) < 2 or segment[-1, 0] - segment[0, 0] < (WINDOW - 1) / RATE:
            continue
        t = np.arange(segment[0, 0], segment[-1, 0], 1 / RATE)
        input_rate = 1 / np.median(np.diff(segment[:, 0]))
        xyz_in = segment[:, 1:4]
        if input_rate > RATE * 1.2:
            sos = butter(4, RATE * .4, fs=input_rate, output='sos')
            xyz_in = sosfiltfilt(sos, xyz_in, axis=0)
        xyz = np.column_stack([np.interp(t, segment[:, 0], xyz_in[:, i]) for i in (0, 1, 2)])
        for start in range(0, len(xyz) - WINDOW + 1, HOP):
            yield xyz[start:start + WINDOW]


def feature_vector(window):
    extractor = ActivityFeatureExtractor(WINDOW, WINDOW-HOP, RATE)
    for sample in window:
        extractor.add_sample(*sample)
    return extractor.extract_features()


def feature_matrix(windows_array):
    """Vectorized equivalent of the streaming feature extractor."""
    data = np.asarray(windows_array)
    magnitude = np.linalg.norm(data, axis=2)
    signals = np.concatenate((np.transpose(data, (0, 2, 1)), magnitude[:, None, :]), axis=1)
    mean = np.mean(signals, axis=2)
    std = np.std(signals, axis=2)
    minimum = np.min(signals, axis=2)
    maximum = np.max(signals, axis=2)
    median = np.median(signals, axis=2)
    power = np.abs(np.fft.rfft(signals - mean[:, :, None], axis=2)) ** 2
    frequencies = np.fft.rfftfreq(WINDOW, d=1 / RATE)
    dominant = np.where(np.any(power[:, :, 1:], axis=2), frequencies[1 + np.argmax(power[:, :, 1:], axis=2)], 0)
    stats = [mean, std, np.var(signals, axis=2), minimum, maximum, maximum-minimum,
             np.sqrt(np.mean(signals**2, axis=2)), median,
             np.median(np.abs(signals-median[:, :, None]), axis=2),
             np.percentile(signals, 25, axis=2), np.percentile(signals, 75, axis=2), dominant]
    return np.stack(stats, axis=2).reshape(len(data), -1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', help='SELFBack Datasets master ZIP')
    parser.add_argument('--model', default='activity_model.pkl')
    parser.add_argument('--report', default='activity_report.json')
    parser.add_argument('--max-windows', type=int, default=40,
                        help='evenly sample at most this many windows per recording; 0 uses all')
    parser.add_argument('--max-subjects', type=int, default=0, help='limit subjects for a quick smoke evaluation; 0 uses all')
    args = parser.parse_args()
    X, y, groups = [], [], []
    for subject, label, samples in rows_from_archive(args.archive, args.max_subjects):
        count = 0
        segments = list(windows(samples))
        if args.max_windows > 0 and len(segments) > args.max_windows:
            indices = np.linspace(0, len(segments)-1, args.max_windows, dtype=int)
            segments = [segments[i] for i in indices]
        if segments:
            features = feature_matrix(segments)
            X.extend(features); y.extend([label] * len(features)); groups.extend([subject] * len(features))
            count = len(features)
        print(f'{subject} {label}: {count} windows', flush=True)
    if not X:
        raise SystemExit('No wrist50 samples found in archive')
    X, y, groups = np.asarray(X), np.asarray(y), np.asarray(groups)
    train, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42).split(X, y, groups))
    if set(y[train]) != set(LABELS.values()) or set(y[test]) != set(LABELS.values()):
        raise SystemExit('Missing class in grouped train/test split')
    model = RandomForestClassifier(n_estimators=100, max_depth=14, min_samples_leaf=2,
                                   class_weight='balanced_subsample', random_state=42, n_jobs=-1)
    model.fit(X[train], y[train]); predicted = model.predict(X[test])
    report = {'dataset': 'SELFBack wrist50, Axivity AX3', 'labels': LABELS, 'max_windows_per_recording': args.max_windows, 'max_subjects': args.max_subjects,
              'excluded': ['downstairs'], 'split': 'subject-held-out',
              'train_subjects': sorted(set(groups[train])), 'test_subjects': sorted(set(groups[test])),
              'classification_report': classification_report(y[test], predicted, output_dict=True, zero_division=0),
              'classes': list(model.classes_), 'confusion_matrix': confusion_matrix(y[test], predicted, labels=model.classes_).tolist()}
    with open(args.report, 'w') as out: json.dump(report, out, indent=2)
    with open(args.model, 'wb') as out:
        pickle.dump({'feature_version': FEATURE_VERSION, 'sample_rate': RATE, 'window': WINDOW,
                     'hop': HOP, 'model': model, 'dataset': report['dataset']}, out)
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
