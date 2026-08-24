"""
model_manager.py — SentiVox Model Management

Handles model file upload, validation, activation (hot-swap), listing, and deletion.
"""

import os
import shutil
import uuid
from datetime import datetime

import numpy as np
import tensorflow as tf
from sqlalchemy.orm import Session

from database import UploadedModel, AppConfig


MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def validate_model_file(file_path: str) -> dict:
    """
    Load an .h5 model file and verify its input/output shapes match
    the expected SER architecture: input=(None, 46, 1), output=(None, 7).
    Returns metadata dict or raises ValueError.
    """
    try:
        model = tf.keras.models.load_model(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load model file: {str(e)}")

    input_shape = model.input_shape
    output_shape = model.output_shape

    # Validate input shape is compatible with (batch, 46, 1)
    if len(input_shape) != 3:
        raise ValueError(f"Expected 3D input shape (batch, 46, 1), got {input_shape}")

    feature_dim = input_shape[1]
    if feature_dim is not None and feature_dim != 46:
        raise ValueError(f"Expected input feature dimension of 46, got {feature_dim}")

    # Validate output shape has 7 classes
    num_classes = output_shape[-1]
    if num_classes != 7:
        raise ValueError(f"Expected 7 output classes, got {num_classes}")

    # Run a sanity forward pass
    dummy_input = np.random.randn(1, 46, 1).astype(np.float32)
    predictions = model.predict(dummy_input, verbose=0)
    if predictions.shape != (1, 7):
        raise ValueError(f"Forward pass returned unexpected shape: {predictions.shape}")

    return {
        "input_shape": str(input_shape),
        "num_classes": int(num_classes),
        "valid": True
    }


def save_model_file(file_content: bytes, original_name: str, user_id: int, db: Session) -> UploadedModel:
    """
    Save an uploaded model file to disk and register it in the database.
    """
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    safe_name = f"model_{timestamp}_{unique_id}.h5"
    file_path = os.path.join(MODELS_DIR, safe_name)

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Validate model structure
    try:
        metadata = validate_model_file(file_path)
    except ValueError as e:
        # Remove invalid file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e

    # Create database record
    model_record = UploadedModel(
        filename=safe_name,
        original_name=original_name,
        file_path=file_path,
        input_shape=metadata["input_shape"],
        num_classes=metadata["num_classes"],
        is_active=False,
        uploaded_by=user_id
    )
    db.add(model_record)
    db.commit()
    db.refresh(model_record)

    return model_record


def activate_model(model_id: int, db: Session, inference_engine) -> UploadedModel:
    """
    Set the specified model as active, deactivate all others,
    update app_configs, and hot-swap the inference engine.
    """
    target_model = db.query(UploadedModel).filter(UploadedModel.id == model_id).first()
    if target_model is None:
        raise ValueError(f"Model with ID {model_id} not found.")

    if not os.path.exists(target_model.file_path):
        raise ValueError(f"Model file not found on disk: {target_model.file_path}")

    # Validate before activating
    validate_model_file(target_model.file_path)

    # Deactivate all models
    db.query(UploadedModel).update({"is_active": False})

    # Activate target model
    target_model.is_active = True

    # Update app_configs
    config = db.query(AppConfig).filter(AppConfig.config_key == "active_model_id").first()
    if config:
        config.config_value = str(model_id)

    db.commit()

    # Hot-swap inference engine
    inference_engine.reload_model(target_model.file_path)

    return target_model


def list_models(db: Session) -> list:
    """List all uploaded models from the database."""
    return db.query(UploadedModel).order_by(UploadedModel.created_at.desc()).all()


def delete_model(model_id: int, db: Session) -> bool:
    """Delete an inactive model from disk and database."""
    model = db.query(UploadedModel).filter(UploadedModel.id == model_id).first()
    if model is None:
        raise ValueError(f"Model with ID {model_id} not found.")

    if model.is_active:
        raise ValueError("Cannot delete the currently active model. Activate a different model first.")

    # Remove file from disk
    if os.path.exists(model.file_path):
        os.remove(model.file_path)

    # Remove DB record
    db.delete(model)
    db.commit()
    return True
