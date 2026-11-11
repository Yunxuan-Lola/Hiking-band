import numpy as np
from collections import deque


class ActivityFeatureExtractor:
    def __init__(self, window_size=50, overlap=25, sample_rate=25.0):
        if window_size < 2 or not 0 <= overlap < window_size or sample_rate <= 0:
            raise ValueError('invalid window, overlap, or sample rate')
        self.window_size = window_size
        self.overlap = overlap
        self.sample_rate = sample_rate
        self.buffer = deque(maxlen=window_size)

    def reset(self):
        self.buffer.clear()

    def add_sample(self, ax, ay, az):
        self.buffer.append((ax, ay, az))

    def has_enough_data(self):
        return len(self.buffer) == self.window_size

    def extract_features(self):
        if not self.has_enough_data():
            return None

        data = np.array(self.buffer)
        ax = data[:, 0]
        ay = data[:, 1]
        az = data[:, 2]

        mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)

        features = []

        features.extend(self._statistical_features(ax, 'ax'))
        features.extend(self._statistical_features(ay, 'ay'))
        features.extend(self._statistical_features(az, 'az'))
        features.extend(self._statistical_features(mag, 'mag'))

        return np.array(features)

    def _statistical_features(self, signal, prefix):
        mean = np.mean(signal)
        std = np.std(signal)
        var = np.var(signal)
        min_val = np.min(signal)
        max_val = np.max(signal)
        range_val = max_val - min_val
        rms = np.sqrt(np.mean(signal ** 2))
        median = np.median(signal)
        mad = np.median(np.abs(signal - median))
        q25 = np.percentile(signal, 25)
        q75 = np.percentile(signal, 75)

        # Remove DC so gravity and axis offsets do not dominate the spectrum.
        spectrum = np.abs(np.fft.rfft(signal - mean)) ** 2
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / self.sample_rate)
        dominant_freq = freqs[1 + np.argmax(spectrum[1:])] if np.any(spectrum[1:]) else 0.0

        return [
            mean, std, var, min_val, max_val, range_val,
            rms, median, mad, q25, q75, dominant_freq
        ]

    @staticmethod
    def get_feature_names():
        axes = ['ax', 'ay', 'az', 'mag']
        stats = ['mean', 'std', 'var', 'min', 'max', 'range',
                 'rms', 'median', 'mad', 'q25', 'q75', 'dominant_freq']
        return [f'{axis}_{stat}' for axis in axes for stat in stats]
