"""
tests/test_system.py — SentiVox Automated Test Suite

All tests use the real API endpoints and database.
Flow: Register → Login → Get Token → Use Token for authenticated requests.
No dummy/hardcoded data — everything goes through the API and DB.
"""

import os
import io
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app


def create_synthetic_wav_bytes(duration_sec=1.5, sample_rate=16000, frequency=440.0):
    """Generate a synthetic sine wave WAV file in memory for testing."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    signal = 0.5 * np.sin(2 * np.pi * frequency * t)
    buffer = io.BytesIO()
    sf.write(buffer, signal, sample_rate, format='WAV', subtype='PCM_16')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture(scope="module")
def api_client():
    """Provide a TestClient connected to the real FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Login as the seeded default admin and return the access token."""
    response = api_client.post("/api/v1/auth/login", json={
        "email": "admin@sentivox.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    data = response.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def user_token(api_client):
    """Register a test user via the API, login, and return the access token."""
    # Attempt registration (ignore if already registered)
    api_client.post("/api/v1/auth/register", json={
        "email": "testuser@sentivox.com",
        "password": "testpass123",
        "full_name": "Test User"
    })

    # Login
    login_response = api_client.post("/api/v1/auth/login", json={
        "email": "testuser@sentivox.com",
        "password": "testpass123"
    })
    assert login_response.status_code == 200, f"User login failed: {login_response.json()}"
    data = login_response.json()
    assert "access_token" in data
    return data["access_token"]


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & SYSTEM TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_health_endpoint(api_client):
    """Health endpoint returns system status."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "SentiVox"
    assert data["model_loaded"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_register_duplicate_email(api_client, user_token):
    """Registering with an already-used email returns 400."""
    response = api_client.post("/api/v1/auth/register", json={
        "email": "testuser@sentivox.com",
        "password": "anotherpass",
        "full_name": "Duplicate User"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_invalid_credentials(api_client):
    """Login with wrong password returns 401."""
    response = api_client.post("/api/v1/auth/login", json={
        "email": "admin@sentivox.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_admin_login_returns_admin_role(api_client):
    """Admin login returns user object with ADMIN role."""
    response = api_client.post("/api/v1/auth/login", json={
        "email": "admin@sentivox.com",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "ADMIN"


def test_user_login_returns_user_role(api_client, user_token):
    """User login returns user object with USER role."""
    response = api_client.post("/api/v1/auth/login", json={
        "email": "testuser@sentivox.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "USER"


def test_refresh_token_flow(api_client):
    """Refresh token returns a new access token."""
    login_resp = api_client.post("/api/v1/auth/login", json={
        "email": "admin@sentivox.com",
        "password": "admin123"
    })
    refresh_tok = login_resp.json()["refresh_token"]

    refresh_resp = api_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_tok
    })
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION TESTS (Authenticated)
# ═══════════════════════════════════════════════════════════════════════════════

def test_predict_requires_auth(api_client):
    """POST /predict without token returns 401."""
    wav_bytes = create_synthetic_wav_bytes()
    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    response = api_client.post("/api/v1/predict", files=files)
    assert response.status_code == 401 or response.status_code == 403


def test_predict_with_user_token(api_client, user_token):
    """Authenticated USER can predict emotion."""
    wav_bytes = create_synthetic_wav_bytes()
    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    headers = {"Authorization": f"Bearer {user_token}"}

    response = api_client.post("/api/v1/predict", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data
    assert "confidence_score" in data
    assert "probability_distribution" in data
    assert len(data["probability_distribution"]) == 7


def test_predict_with_admin_token(api_client, admin_token):
    """Authenticated ADMIN can also predict emotion."""
    wav_bytes = create_synthetic_wav_bytes()
    files = {"file": ("admin_test.wav", wav_bytes, "audio/wav")}
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = api_client.post("/api/v1/predict", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_class" in data


def test_unsupported_file_rejection(api_client, user_token):
    """Uploading .txt file returns 415."""
    headers = {"Authorization": f"Bearer {user_token}"}
    files = {"file": ("doc.txt", b"plain text", "text/plain")}
    response = api_client.post("/api/v1/predict", files=files, headers=headers)
    assert response.status_code == 415


def test_prediction_history(api_client, user_token):
    """User can view their own prediction history from the DB."""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = api_client.get("/api/v1/predictions/history", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least the prediction from test_predict_with_user_token
    assert len(data) >= 1
    assert "predicted_class" in data[0]
    assert "confidence_score" in data[0]


# ═══════════════════════════════════════════════════════════════════════════════
# ACL TESTS (Admin vs. User)
# ═══════════════════════════════════════════════════════════════════════════════

def test_user_cannot_access_admin_models(api_client, user_token):
    """USER role gets 403 when accessing admin-only model endpoints."""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = api_client.get("/api/v1/admin/models", headers=headers)
    assert response.status_code == 403


def test_user_cannot_update_config(api_client, user_token):
    """USER role gets 403 when trying to update config."""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = api_client.put("/api/v1/admin/config", headers=headers, json={
        "config_key": "app_name",
        "config_value": "Hacked"
    })
    assert response.status_code == 403


def test_admin_can_list_models(api_client, admin_token):
    """ADMIN can list all uploaded models from the DB."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = api_client.get("/api/v1/admin/models", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # At least the seeded development model


def test_admin_can_list_users(api_client, admin_token):
    """ADMIN can list all registered users from the DB."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = api_client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # admin + testuser


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_authenticated_user_can_read_config(api_client, user_token):
    """Authenticated user can read application config from the DB."""
    headers = {"Authorization": f"Bearer {user_token}"}
    response = api_client.get("/api/v1/config", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    keys = [c["config_key"] for c in data]
    assert "app_name" in keys
    assert "active_model_id" in keys


def test_admin_can_update_config(api_client, admin_token):
    """ADMIN can update a config value in the DB."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = api_client.put("/api/v1/admin/config", headers=headers, json={
        "config_key": "app_name",
        "config_value": "SentiVox Pro"
    })
    assert response.status_code == 200
    assert response.json()["config_value"] == "SentiVox Pro"

    # Verify the change persists when reading config
    read_resp = api_client.get("/api/v1/config", headers=headers)
    configs = {c["config_key"]: c["config_value"] for c in read_resp.json()}
    assert configs["app_name"] == "SentiVox Pro"
