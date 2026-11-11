import numpy as np
import pickle
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler


class ActivityClassifier:
    def __init__(self, model_path='activity_model.pkl', scaler_path='scaler.pkl'):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = None
        self.classes = ['idle', 'walking', 'jogging', 'running']

    def train(self, X, y):
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train_scaled, y_train)

        y_pred = self.model.predict(X_test_scaled)
        print("Model Evaluation:")
        print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=self.classes))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))

        return self.model, self.scaler

    def save(self):
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"Model saved to {self.model_path}")
        print(f"Scaler saved to {self.scaler_path}")

    def load(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.scaler_path):
            raise FileNotFoundError("Model or scaler files not found")

        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(self.scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        print("Model and scaler loaded successfully")
        return self

    def predict(self, features):
        if features is None:
            return None

        features_scaled = self.scaler.transform([features])
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        return {
            'activity': self.classes[prediction],
            'probability': float(max(probabilities)),
            'all_probabilities': {
                self.classes[i]: float(prob)
                for i, prob in enumerate(probabilities)
            }
        }


def generate_synthetic_data(num_samples_per_class=1000):
    from features import ActivityFeatureExtractor

    np.random.seed(42)
    extractor = ActivityFeatureExtractor(window_size=50)

    X = []
    y = []

    for class_idx, activity in enumerate(['idle', 'walking', 'jogging', 'running']):
        print(f"Generating {activity} data...")
        for _ in range(num_samples_per_class):
            extractor.reset()

            if activity == 'idle':
                ax = np.random.normal(0, 0.1, 50)
                ay = np.random.normal(0, 0.1, 50) - 1
                az = np.random.normal(0, 0.1, 50)
            elif activity == 'walking':
                t = np.linspace(0, 2 * np.pi, 50)
                ax = np.sin(t * 2) * 0.5 + np.random.normal(0, 0.1, 50)
                ay = np.cos(t * 2) * 0.2 - 1 + np.random.normal(0, 0.1, 50)
                az = np.sin(t * 4) * 0.3 + np.random.normal(0, 0.1, 50)
            elif activity == 'jogging':
                t = np.linspace(0, 2 * np.pi, 50)
                ax = np.sin(t * 4) * 1.5 + np.random.normal(0, 0.3, 50)
                ay = np.cos(t * 4) * 0.8 - 1 + np.random.normal(0, 0.2, 50)
                az = np.sin(t * 8) * 1.0 + np.random.normal(0, 0.2, 50)
            elif activity == 'running':
                t = np.linspace(0, 2 * np.pi, 50)
                ax = np.sin(t * 8) * 3.0 + np.random.normal(0, 0.5, 50)
                ay = np.cos(t * 8) * 1.5 - 1 + np.random.normal(0, 0.4, 50)
                az = np.sin(t * 16) * 2.0 + np.random.normal(0, 0.4, 50)

            for i in range(50):
                extractor.add_sample(ax[i], ay[i], az[i])

            features = extractor.extract_features()
            X.append(features)
            y.append(class_idx)

    return np.array(X), np.array(y)


if __name__ == "__main__":
    raise SystemExit('Legacy synthetic demo is not a deployable model. Use train_public.py with the SELFBack archive.')
