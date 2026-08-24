"""
server.py — SentiVox Enterprise REST API Service

Full-stack FastAPI backend with:
- JWT Authentication (register, login, refresh)
- Role-Based ACL (ADMIN / USER)
- Dynamic Application Config (DB-backed key-value store)
- Model Upload, Validation & Hot-Swap Management
- Prediction with history logging
- Rate limiting on sensitive endpoints
- Structured error handling with request IDs
- Static Web Dashboard serving
"""

import os
import sys
import tempfile
import time
import uuid
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    CORS_ORIGINS, MAX_FILE_SIZE_BYTES, MAX_BATCH_FILES,
    ALLOWED_AUDIO_EXTENSIONS, IS_PRODUCTION, ENV,
    RATE_LIMIT_AUTH, RATE_LIMIT_PREDICT, HOST, PORT
)
from database import get_db, init_database, User, AppConfig, UploadedModel, PredictionLog
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, require_role
)
from schemas import (
    UserRegister, UserLogin, UserProfile, TokenResponse, RefreshTokenRequest,
    ConfigUpdate, ConfigResponse, ModelResponse, PredictionLogResponse, MessageResponse
)
from inference_engine import SERInferenceEngine
from logging_config import setup_logging, get_logger
import model_manager

# Initialize logging FIRST
setup_logging()
logger = get_logger("server")

# Global Inference Engine Reference
engine = None

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown lifecycle manager."""
    global engine
    logger.info("=" * 60)
    logger.info("  SentiVox — Speech Emotion Recognition Platform")
    logger.info("  Environment: %s", ENV)
    logger.info("=" * 60)
    logger.info("Initializing database and seeding defaults...")
    init_database()
    logger.info("Loading inference engine...")
    try:
        engine = SERInferenceEngine()
        logger.info("SentiVox is ready! Listening on %s:%d", HOST, PORT)
    except Exception as e:
        logger.error("Failed to initialize inference engine: %s", str(e), exc_info=True)
        logger.warning("Server starting WITHOUT model — predictions will be unavailable")
    yield
    logger.info("Shutting down SentiVox...")


app = FastAPI(
    title="SentiVox API",
    description="Enterprise Speech Emotion Recognition Platform with Authentication, ACL & Model Management",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ─── Request Middleware ───────────────────────────────────────────────────────

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Add request ID and logging context to every request."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 1)

    # Log request (skip health checks in production to reduce noise)
    if not (IS_PRODUCTION and request.url.path in ("/health", "/ready")):
        logger.info(
            "[%s] %s %s → %d (%.1fms)",
            request_id, request.method, request.url.path,
            response.status_code, duration_ms
        )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    return response


# ─── Global Exception Handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to prevent stack traces from leaking to clients."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "[%s] Unhandled exception on %s %s: %s",
        request_id, request.method, request.url.path, str(exc),
        exc_info=True
    )

    # In development, return the actual error; in production, return generic message
    detail = str(exc) if not IS_PRODUCTION else "An internal server error occurred."
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request_id}
    )


def validate_audio_file(file: UploadFile):
    """Validate file extension."""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}"
        )


def _require_engine():
    """Guard: ensure inference engine is loaded before prediction."""
    if engine is None or not engine.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Inference engine is not available. The model may still be loading."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & READINESS CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health", summary="Health Status & System Diagnostics", tags=["System"])
async def health_check():
    """Return API health status, hardware info, and model state."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    return {
        "status": "healthy",
        "app_name": "SentiVox",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "3.1.0",
        "environment": ENV,
        "model_loaded": engine is not None and engine.is_ready,
        "hardware": {
            "gpu_available": len(gpus) > 0,
            "gpu_device": gpus[0].name if gpus else "N/A (CPU)",
            "python_version": sys.version.split()[0],
            "tensorflow_version": tf.__version__
        }
    }


@app.get("/ready", summary="Readiness Probe", tags=["System"])
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes/load-balancer readiness probe.
    Returns 200 only when both the model and database are operational.
    """
    errors = []

    # Check model readiness
    if engine is None or not engine.is_ready:
        errors.append("Inference engine not ready")

    # Check database connectivity
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"Database unreachable: {str(e)}")

    if errors:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "errors": errors}
        )

    return {"ready": True}


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/auth/register", response_model=MessageResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMIT_AUTH)
async def register(request: Request, body: UserRegister, db: Session = Depends(get_db)):
    """Register a new USER account."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="USER",
        is_active=True
    )
    db.add(user)
    db.commit()

    logger.info("New user registered: %s", body.email)
    return {"message": "Registration successful.", "detail": f"Account created for {body.email}"}


@app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, body: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and receive JWT access & refresh tokens."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        logger.warning("Failed login attempt for email: %s", body.email)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)

    logger.info("User logged in: %s (role=%s)", user.email, user.role)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserProfile.model_validate(user)
    }


@app.post("/api/v1/auth/refresh", tags=["Authentication"])
@limiter.limit(RATE_LIMIT_AUTH)
async def refresh_token(request: Request, body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh an expired access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    new_access = create_access_token(user.id, user.email, user.role)
    return {"access_token": new_access, "token_type": "bearer"}


# ═══════════════════════════════════════════════════════════════════════════════
# USER ROUTES (Authenticated)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/users/me", response_model=UserProfile, tags=["User"])
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserProfile.model_validate(current_user)


@app.get("/api/v1/config", response_model=List[ConfigResponse], tags=["Configuration"])
async def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all public application configuration settings."""
    configs = db.query(AppConfig).all()
    return [ConfigResponse.model_validate(c) for c in configs]


# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTION ROUTES (Authenticated)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/predict", summary="Predict Emotion from Audio", tags=["Prediction"])
@limiter.limit(RATE_LIMIT_PREDICT)
async def predict_single(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accepts audio file and returns predicted emotion with confidence distribution. Requires authentication."""
    _require_engine()
    validate_audio_file(file)

    temp_path = None
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)}MB limit.")
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tempfile.gettempdir()) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        result = engine.predict(temp_path)
        result["filename"] = file.filename

        # Log prediction to database
        log_entry = PredictionLog(
            user_id=current_user.id,
            audio_filename=file.filename or "",
            predicted_class=result["predicted_class"],
            confidence_score=result["confidence_score"],
            probability_distribution=result["probability_distribution"],
            inference_latency_ms=result["inference_latency_ms"]
        )
        db.add(log_entry)
        db.commit()

        return JSONResponse(status_code=200, content=result)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Inference error for user_id=%d: %s", current_user.id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Failed to clean up temp file: %s", temp_path)


@app.post("/api/v1/predict/batch", summary="Batch Predict Emotion", tags=["Prediction"])
@limiter.limit(RATE_LIMIT_PREDICT)
async def predict_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accepts up to 20 audio files. Requires authentication."""
    _require_engine()

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_BATCH_FILES} files per batch.")

    results = []
    for file in files:
        validate_audio_file(file)
        temp_path = None
        try:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                results.append({"filename": file.filename, "error": f"File exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"})
                continue
            if len(content) == 0:
                results.append({"filename": file.filename, "error": "File is empty"})
                continue

            ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tempfile.gettempdir()) as tmp:
                tmp.write(content)
                temp_path = tmp.name

            prediction = engine.predict(temp_path)
            prediction["filename"] = file.filename

            log_entry = PredictionLog(
                user_id=current_user.id,
                audio_filename=file.filename or "",
                predicted_class=prediction["predicted_class"],
                confidence_score=prediction["confidence_score"],
                probability_distribution=prediction["probability_distribution"],
                inference_latency_ms=prediction["inference_latency_ms"]
            )
            db.add(log_entry)
            results.append(prediction)

        except Exception as e:
            logger.warning("Batch predict error for file %s: %s", file.filename, str(e))
            results.append({"filename": file.filename, "error": str(e)})
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to commit batch prediction logs: %s", str(e))

    return JSONResponse(status_code=200, content={"total_files": len(files), "results": results})


@app.get("/api/v1/predictions/history", response_model=List[PredictionLogResponse], tags=["Prediction"])
async def prediction_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's prediction history (most recent first)."""
    logs = (
        db.query(PredictionLog)
        .filter(PredictionLog.user_id == current_user.id)
        .order_by(PredictionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [PredictionLogResponse.model_validate(log) for log in logs]


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ROUTES (Admin Only)
# ═══════════════════════════════════════════════════════════════════════════════

@app.put("/api/v1/admin/config", response_model=ConfigResponse, tags=["Admin"])
async def update_config(
    body: ConfigUpdate,
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Update a dynamic application config setting. Admin only."""
    config = db.query(AppConfig).filter(AppConfig.config_key == body.config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{body.config_key}' not found.")

    old_value = config.config_value
    config.config_value = body.config_value
    config.updated_by = admin.email
    db.commit()
    db.refresh(config)

    logger.info(
        "Config updated by %s: %s = '%s' (was '%s')",
        admin.email, body.config_key, body.config_value, old_value
    )
    return ConfigResponse.model_validate(config)


@app.get("/api/v1/admin/models", response_model=List[ModelResponse], tags=["Admin"])
async def list_all_models(
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """List all uploaded models with metadata. Admin only."""
    models = model_manager.list_models(db)
    return [ModelResponse.model_validate(m) for m in models]


@app.post("/api/v1/admin/models/upload", response_model=ModelResponse, tags=["Admin"])
async def upload_model(
    file: UploadFile = File(...),
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Upload and validate a new .h5 model file. Admin only."""
    filename = file.filename or ""
    if not filename.endswith(".h5") and not filename.endswith(".keras"):
        raise HTTPException(status_code=415, detail="Only .h5 or .keras model files are accepted.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded model file is empty.")

    try:
        record = model_manager.save_model_file(content, filename, admin.id, db)
        return ModelResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/v1/admin/models/{model_id}/activate", response_model=ModelResponse, tags=["Admin"])
async def activate_model_endpoint(
    model_id: int,
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Activate a model for inference (hot-swap). Admin only."""
    try:
        activated = model_manager.activate_model(model_id, db, engine)
        return ModelResponse.model_validate(activated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/admin/models/{model_id}", response_model=MessageResponse, tags=["Admin"])
async def delete_model_endpoint(
    model_id: int,
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """Delete an inactive model. Admin only."""
    try:
        model_manager.delete_model(model_id, db)
        return {"message": f"Model {model_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/admin/users", response_model=List[UserProfile], tags=["Admin"])
async def list_users(
    admin: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """List all registered users. Admin only."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [UserProfile.model_validate(u) for u in users]


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC WEB DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "SentiVox API active. Add index.html to static/ for UI."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=HOST, port=PORT, reload=not IS_PRODUCTION)
