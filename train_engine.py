"""
train_engine.py — Module 2: Deep Learning Architecture & Training Engine

Objective: Train and validate the high-accuracy 1D Convolutional Neural Network (CascadeCovM1).
Architecture Specification:
- Input Shape: (46, 1)
- 3 Conv1D Blocks (180, 180, 360 filters) with MaxPool(2) and Dropout(0.2)
- Dense Head (720 -> 360 -> 180 -> 90 -> 7) with Dropout(0.3)
"""

import os
import argparse
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout, Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import SparseCategoricalCrossentropy
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard, ReduceLROnPlateau


def build_cascade_cov_m1(input_shape=(46, 1), num_classes=7):
    """
    Build the CascadeCovM1 1D Convolutional Neural Network.
    """
    model = Sequential([
        Input(shape=input_shape),

        # Block 1
        Conv1D(filters=180, kernel_size=3, padding='same', activation='relu'),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # Block 2
        Conv1D(filters=180, kernel_size=3, padding='same', activation='relu'),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # Block 3
        Conv1D(filters=360, kernel_size=3, padding='same', activation='relu'),
        MaxPooling1D(pool_size=2),
        Dropout(0.2),

        # Flatten & Classification Head
        Flatten(),
        Dense(720, activation='relu'),
        Dropout(0.3),
        Dense(360, activation='relu'),
        Dropout(0.3),
        Dense(180, activation='relu'),
        Dropout(0.3),
        Dense(90, activation='relu'),
        Dense(num_classes, activation='softmax')
    ], name="CascadeCovM1")

    return model


def compile_model(model, learning_rate=0.0001):
    """Compile model with Adam optimizer and SparseCategoricalCrossentropy loss."""
    optimizer = Adam(learning_rate=learning_rate)
    loss = SparseCategoricalCrossentropy()
    metrics = ['accuracy']

    model.compile(optimizer=optimizer, loss=loss, metrics=metrics)
    return model


def get_callbacks(log_dir="./logs/fit", checkpoint_dir="models"):
    """Prepare production callbacks: EarlyStopping, ModelCheckpoint, TensorBoard, ReduceLROnPlateau."""
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    checkpoint_path = os.path.join(checkpoint_dir, "CascadeCovM1_BEST.h5")

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
        ModelCheckpoint(filepath=checkpoint_path, monitor='val_accuracy', save_best_only=True, verbose=1),
        TensorBoard(log_dir=log_dir, histogram_freq=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
    ]
    return callbacks, checkpoint_path


def train_model(features_path="data/features.npz", epochs=100, batch_size=32, learning_rate=0.0001):
    """Load preprocessed features and train the CascadeCovM1 network."""
    if not os.path.exists(features_path):
        raise FileNotFoundError(f"Feature file not found at {features_path}. Run dataset_pipeline.py first.")

    data = np.load(features_path)
    X_train = data['X_train']
    y_train = data['y_train']
    X_test = data['X_test']
    y_test = data['y_test']

    # Reshape input vectors to (N, 46, 1) for Conv1D
    X_train = np.expand_dims(X_train, axis=-1)
    X_test = np.expand_dims(X_test, axis=-1)

    print(f"[+] Loaded Dataset: X_train={X_train.shape}, y_train={y_train.shape}, X_test={X_test.shape}, y_test={y_test.shape}")

    model = build_cascade_cov_m1(input_shape=(46, 1), num_classes=7)
    model = compile_model(model, learning_rate=learning_rate)
    model.summary()

    callbacks, best_model_path = get_callbacks()

    print("[+] Starting model training...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks
    )

    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"[✓] Training Completed! Test Loss: {test_loss:.4f}, Test Accuracy: {test_acc:.4f}")
    print(f"[✓] Best model saved to: {best_model_path}")
    return model, history


def generate_dummy_model(output_path="models/CascadeCovM1_BEST.h5"):
    """
    Generate an initialized CascadeCovM1 model file for API development and testing
    when dataset is not yet present.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model = build_cascade_cov_m1(input_shape=(46, 1), num_classes=7)
    model = compile_model(model)

    # Perform a single forward pass with synthetic data to build shapes
    dummy_input = np.random.randn(2, 46, 1).astype(np.float32)
    model.predict(dummy_input, verbose=0)

    model.save(output_path)
    print(f"[✓] Generated development model at: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CascadeCovM1 Speech Emotion Recognition Model")
    parser.add_argument("--features", type=str, default="data/features.npz", help="Path to preprocessed features file")
    parser.add_argument("--epochs", type=int, default=100, help="Max training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate")
    parser.add_argument("--create-dummy", action="store_true", help="Generate a initialized model file for development")

    args = parser.parse_args()

    if args.create_dummy:
        generate_dummy_model()
    else:
        train_model(features_path=args.features, epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr)
