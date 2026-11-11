import logging
import pickle
from pathlib import Path
from features import ActivityFeatureExtractor


class ActivityRecognition:
    def __init__(self, model_path=None, verbose=True):
        self.extractor = ActivityFeatureExtractor(window_size=50, overlap=25, sample_rate=25)
        self.classifier = None
        self.model_path = Path(model_path) if model_path else Path(__file__).parent / 'activity_model.pkl'
        self.verbose = verbose
        self.is_ready = False
        self.sample_count = 0
        self.activity_counts = {'idle': 0, 'walking': 0, 'climbing': 0, 'running': 0}
        self.current_activity = 'unknown'
        self.last_prediction = None

    def initialize(self):
        try:
            # Pickle is executable: only load model files obtained from trusted sources.
            with self.model_path.open('rb') as source:
                artifact = pickle.load(source)
            if artifact.get('feature_version') != 2:
                raise ValueError('unsupported model feature version')
            window = artifact['window']; hop = artifact['hop']
            self.extractor = ActivityFeatureExtractor(window, window-hop, artifact['sample_rate'])
            self.classifier = artifact['model']
            self.is_ready = True
            logging.info("Activity recognition model loaded successfully")
            return True
        except (FileNotFoundError, ValueError, KeyError, pickle.UnpicklingError) as exc:
            logging.warning("Model unavailable: %s", exc)
            return False

    def add_imu_sample(self, ax, ay, az):
        self.extractor.add_sample(ax, ay, az)
        self.sample_count += 1

        hop = self.extractor.window_size - self.extractor.overlap
        if (self.extractor.has_enough_data() and self.is_ready and
                (self.sample_count - self.extractor.window_size) % hop == 0):
            features = self.extractor.extract_features()
            if features is not None:
                probabilities = self.classifier.predict_proba([features])[0]
                index = int(probabilities.argmax())
                prediction = {'activity': str(self.classifier.classes_[index]),
                              'probability': float(probabilities[index]),
                              'all_probabilities': dict(zip(self.classifier.classes_, map(float, probabilities)))}
                if prediction:
                    self.last_prediction = prediction
                    activity = prediction['activity']
                    if activity in self.activity_counts:
                        self.activity_counts[activity] += 1
                    self.current_activity = activity
                    logging.info("Detected activity: %s (prob: %.2f)", activity, prediction['probability'])
                    if self.verbose:
                        print(f"Activity: {activity} (confidence: {prediction['probability']:.2f})", flush=True)

    def get_dominant_activity(self):
        if sum(self.activity_counts.values()) == 0:
            return 'unknown'
        return max(self.activity_counts, key=self.activity_counts.get)

    def get_activity_distribution(self):
        total = sum(self.activity_counts.values())
        if total == 0:
            return {k: 0.0 for k in self.activity_counts}
        return {k: v / total for k, v in self.activity_counts.items()}

    def reset(self):
        self.extractor.reset()
        self.sample_count = 0
        self.activity_counts = {'idle': 0, 'walking': 0, 'climbing': 0, 'running': 0}
        self.current_activity = 'unknown'
        self.last_prediction = None

    def reset_window(self):
        """Discard incomplete windows without losing session totals."""
        self.extractor.reset()
        self.sample_count = 0
        self.current_activity = 'unknown'
        self.last_prediction = None

    def get_current_status(self):
        return {
            'current_activity': self.current_activity,
            'dominant_activity': self.get_dominant_activity(),
            'distribution': self.get_activity_distribution(),
            'sample_count': self.sample_count,
            'last_prediction': self.last_prediction
        }
