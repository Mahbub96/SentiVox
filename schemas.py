"""
schemas.py — SentiVox Pydantic Request/Response Models

Defines strict validation schemas for all API endpoints.
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ─── Authentication Schemas ───────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, examples=["user@example.com"])
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255, examples=["Mahbub Alam"])


class UserLogin(BaseModel):
    email: str = Field(..., examples=["admin@sentivox.com"])
    password: str = Field(..., examples=["admin123"])


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ─── Application Config Schemas ──────────────────────────────────────────────

class ConfigUpdate(BaseModel):
    config_key: str
    config_value: str


class ConfigResponse(BaseModel):
    config_key: str
    config_value: str
    description: str
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Model Management Schemas ────────────────────────────────────────────────

class ModelResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    input_shape: Optional[str] = None
    num_classes: Optional[int] = None
    accuracy: Optional[float] = None
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Prediction Log Schemas ──────────────────────────────────────────────────

class PredictionLogResponse(BaseModel):
    id: int
    audio_filename: Optional[str] = None
    predicted_class: str
    confidence_score: float
    probability_distribution: Optional[Dict[str, float]] = None
    inference_latency_ms: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Generic Response Schemas ────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
