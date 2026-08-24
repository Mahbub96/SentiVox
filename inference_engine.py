"""
inference_engine.py — Module 3: Production Inference Engine

Objective: Stateless, thread-safe class for transforming raw audio into structured emotion predictions.
Features:
- Thread-safe singleton pattern for loading model once into memory
- Accepts raw byte-streams, file paths, and base64-encoded audio strings
- Automatic silence trimming via librosa
- Feature shape strictly matching (1, 46, 1)
- Structured JSON output with latency measurement
"""

import os
import io
import time
import base64
import threading
import numpy as np
import librosa
import soundfile as sf
import tensorflow as tf
from sklearn.preprocessing import normalize

EMOTION_LABEL_MAP = {
    0: 'happy',
    1: 'sad',
    2: 'angry',
    3: 'surprised',
    4: 'neutral',
    5: 'disgust',
    6: 'fear'
}


class SERInferenceEngine:
    """Thread-safe singleton inference engine for Speech Emotion Recognition."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, model_path="models/CascadeCovM1_BEST.h5"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SERInferenceEngine, cls).__new__(cls)
                cls._instance._init_engine(model_path)
            return cls._instance

    def _init_engine(self, model_path):
        """Initialize and load the trained Keras model."""
        self.model_path = model_path
        if not os.path.exists(model_path):
            # Attempt fallback or auto-generate dummy model for development
            from train_engine import generate_dummy_model
            print(f"[!] Model file {model_path} not found. Auto-generating development model...")
            generate_dummy_model(model_path)

        print(f"[+] Loading SER Keras model from: {model_path}")
        self.model = tf.keras.models.load_model(model_path)
        # Perform warmup prediction
        dummy_tensor = np.zeros((1, 46, 1), dtype=np.float32)
        self.model.predict(dummy_tensor, verbose=0)
        print("[✓] Model loaded and warmed up successfully.")

    def extract_features_from_audio(self, audio_data, sample_rate=16000):
        """
        Extract 46-dim normalized feature vector (MFCC 40 + Tonnetz 6) from audio array.
        """
        if len(audio_data) == 0:
            raise ValueError("Audio data signal is empty.")

        # Trim silence (top_db=25)
        audio_trimmed, _ = librosa.effects.trim(audio_data, top_db=25)

        if len(audio_trimmed) == 0:
            audio_trimmed = audio_data  # Fallback if trimming removes everything

        # Extract 40 MFCC features
        mfcc = np.mean(librosa.feature.mfcc(y=audio_trimmed, sr=sample_rate, n_mfcc=40).T, axis=0)

        # Extract 6 Tonnetz features
        y_harmonic = librosa.effects.harmonic(audio_trimmed)
        tonnetz = np.mean(librosa.feature.tonnetz(y=y_harmonic, sr=sample_rate).T, axis=0)

        # Combine vector (46 dimensions)
        raw_vector = np.hstack((mfcc, tonnetz)).astype(np.float32)

        # Reshape for sklearn normalize (requires 2D array)
        raw_vector_2d = raw_vector.reshape(1, -1)

        # Apply L1 normalization
        norm_vector = normalize(raw_vector_2d, axis=1, norm='l1')

        # Reshape to 3D tensor shape (1, 46, 1) for Conv1D
        tensor_input = norm_vector.reshape(1, 46, 1).astype(np.float32)
        return tensor_input

    def decode_audio_source(self, audio_source, sample_rate=16000):
        """
        Decode input audio from file path, raw bytes, or base64 string into numpy audio array.
        """
        # Case 1: Audio is a file path string
        if isinstance(audio_source, str) and os.path.exists(audio_source):
            y, sr = librosa.load(audio_source, sr=sample_rate, mono=True)
            return y, sr

        # Case 2: Audio is a base64 encoded string
        if isinstance(audio_source, str):
            if audio_source.startswith("data:audio") or ";base64," in audio_source:
                audio_source = audio_source.split(";base64,")[-1]
            raw_bytes = base64.b64decode(audio_source)
            buffer = io.BytesIO(raw_bytes)
            y, sr = librosa.load(buffer, sr=sample_rate, mono=True)
            return y, sr

        # Case 3: Audio is raw bytes (io.BytesIO or bytes)
        if isinstance(audio_source, (bytes, bytearray, io.BytesIO)):
            if isinstance(audio_source, (bytes, bytearray)):
                buffer = io.BytesIO(audio_source)
            else:
                buffer = audio_source
            y, sr = librosa.load(buffer, sr=sample_rate, mono=True)
            return y, sr

        raise ValueError("Unsupported audio source type or file not found.")

    def reload_model(self, new_model_path):
        """
        Thread-safe hot-swap: load a new model into memory replacing the current one.
        Called by model_manager.activate_model() when admin activates a different model.
        """
        with self._lock:
            if not os.path.exists(new_model_path):
                raise FileNotFoundError(f"Model file not found: {new_model_path}")

            print(f"[↻] Hot-swapping model to: {new_model_path}")
            new_model = tf.keras.models.load_model(new_model_path)

            # Warmup pass
            dummy_tensor = np.zeros((1, 46, 1), dtype=np.float32)
            new_model.predict(dummy_tensor, verbose=0)

            # Swap reference
            self.model = new_model
            self.model_path = new_model_path
            print(f"[✓] Model hot-swapped successfully to: {new_model_path}")

    def predict(self, audio_source):
        """
        Perform emotion inference on audio input. Returns structured result dict.
        """
        start_time = time.perf_counter()

        # Load and decode audio
        y_audio, sr = self.decode_audio_source(audio_source)

        # Extract normalized 46-dim feature tensor
        input_tensor = self.extract_features_from_audio(y_audio, sample_rate=sr)

        # Model forward pass
        probabilities = self.model.predict(input_tensor, verbose=0)[0]

        # Process output probabilities
        winning_class_idx = int(np.argmax(probabilities))
        confidence_score = float(probabilities[winning_class_idx])
        predicted_class = EMOTION_LABEL_MAP.get(winning_class_idx, "unknown")

        prob_dist = {
            EMOTION_LABEL_MAP[i]: float(round(prob, 4))
            for i, prob in enumerate(probabilities)
        }

        latency_ms = float(round((time.perf_counter() - start_time) * 1000, 2))

        return {
            "predicted_class": predicted_class,
            "class_index": winning_class_idx,
            "confidence_score": float(round(confidence_score, 4)),
            "probability_distribution": prob_dist,
            "inference_latency_ms": latency_ms
        }
