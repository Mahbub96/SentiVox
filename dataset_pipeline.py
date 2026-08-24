"""
dataset_pipeline.py — Module 1: Data Preprocessing & Validation Pipeline

Objective: Extract acoustic features safely without memory crashes or data leakage.
Target Classes:
  0: Happy, 1: Sad, 2: Angry, 3: Surprised, 4: Neutral, 5: Disgust, 6: Fear
Features:
  MFCC (40 dims) + Tonnetz (6 dims) = 46 dimensions
"""

import os
import glob
import random
import logging
import argparse
import numpy as np
import soundfile as sf
import librosa
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import normalize

# Configure logging
logging.basicConfig(
    filename='corrupted_files.log',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

EMOTION_MAP = {
    '01': 0,  # happy
    '02': 1,  # sad
    '03': 2,  # angry
    '04': 3,  # surprised
    '05': 4,  # neutral
    '06': 5,  # disgust
    '07': 6   # fear
}

LABEL_NAMES = {
    0: 'happy',
    1: 'sad',
    2: 'angry',
    3: 'surprised',
    4: 'neutral',
    5: 'disgust',
    6: 'fear'
}


def set_global_seed(seed=42):
    """Set random seed across os, random, numpy, and tensorflow."""
    os.environ['PYTHONHASHSEED'] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
    except ImportError:
        pass


def extract_audio_features(file_path, sample_rate=16000, n_mfcc=40):
    """
    Load audio, resample to 16,000 Hz Mono, trim silence, and extract
    MFCC (40 dims) + Tonnetz (6 dims) = 46-dimensional feature vector.
    """
    try:
        # Load audio file with librosa (resamples to target sample_rate and converts to mono)
        y, sr = librosa.load(file_path, sr=sample_rate, mono=True)

        if len(y) == 0:
            logging.warning(f"Empty audio file: {file_path}")
            return None

        # Trim silence
        y, _ = librosa.effects.trim(y, top_db=25)

        if len(y) == 0:
            logging.warning(f"Audio file became empty after silence trimming: {file_path}")
            return None

        # Extract MFCC (40 features)
        mfcc = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc).T, axis=0)

        # Extract Tonnetz (6 features)
        # Tonnetz requires harmonic component of audio
        y_harmonic = librosa.effects.harmonic(y)
        tonnetz = np.mean(librosa.feature.tonnetz(y=y_harmonic, sr=sr).T, axis=0)

        # Combine into 46-dim vector
        feature_vector = np.hstack((mfcc, tonnetz))
        return feature_vector

    except Exception as e:
        logging.warning(f"Error processing {file_path}: {str(e)}")
        return None


def process_dataset(data_root):
    """
    Recursively find .wav files, parse emotion label from RAVDESS-style filenames,
    and extract features.
    """
    X, y = [], []
    search_pattern = os.path.join(data_root, "**", "*.wav")
    wav_files = glob.glob(search_pattern, recursive=True)

    if not wav_files:
        print(f"[!] Warning: No .wav files found in search path: {search_pattern}")
        return np.array(X), np.array(y)

    print(f"[+] Found {len(wav_files)} audio files. Starting feature extraction...")

    success_count = 0
    for idx, file_path in enumerate(wav_files, 1):
        filename = os.path.basename(file_path)
        parts = filename.split('-')

        # RAVDESS format: 03-01-01-01-01-01-01.wav -> parts[2] is emotion code
        emotion_code = None
        if len(parts) >= 3 and parts[2] in EMOTION_MAP:
            emotion_code = parts[2]
        else:
            # Fallback label search if format varies
            for code, name in EMOTION_MAP.items():
                if LABEL_NAMES[name] in filename.lower():
                    emotion_code = code
                    break

        if emotion_code is None:
            logging.warning(f"Could not determine emotion label for file: {file_path}")
            continue

        label = EMOTION_MAP[emotion_code]
        features = extract_audio_features(file_path)

        if features is not None and len(features) == 46:
            X.append(features)
            y.append(label)
            success_count += 1

        if idx % 100 == 0 or idx == len(wav_files):
            print(f"    Processed {idx}/{len(wav_files)} files ({success_count} successful)...")

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def run_pipeline(data_root, output_path="data/features.npz", test_size=0.2, seed=42):
    """
    Run full preprocessing pipeline adhering strictly to Zero Data Leakage Rule.
    Splits data before applying L1 normalization.
    """
    set_global_seed(seed)

    X, y = process_dataset(data_root)

    if len(X) == 0:
        print("[!] Error: No valid feature vectors extracted. Check data root directory.")
        return False

    print(f"[+] Extracted dataset shape: X={X.shape}, y={y.shape}")

    # Zero Data Leakage Rule: Split train/test BEFORE applying normalization
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed
    )

    print(f"[+] Train/Test Split: Train={X_train.shape[0]}, Test={X_test.shape[0]}")

    # Apply L1 normalization separately to train and test sets
    X_train_norm = normalize(X_train, axis=1, norm='l1')
    X_test_norm = normalize(X_test, axis=1, norm='l1')

    # Save to compressed npz format
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    np.savez_compressed(
        output_path,
        X_train=X_train_norm,
        X_test=X_test_norm,
        y_train=y_train,
        y_test=y_test
    )

    print(f"[✓] Feature dataset successfully exported to: {output_path}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SER Data Preprocessing & Validation Pipeline")
    parser.add_argument("--data-root", type=str, default="./data/BanglaSpeechData", help="Root directory containing audio files")
    parser.add_argument("--output", type=str, default="data/features.npz", help="Output .npz feature file path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()
    run_pipeline(args.data_root, args.output, seed=args.seed)
