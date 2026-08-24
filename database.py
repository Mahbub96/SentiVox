"""
database.py — SentiVox Database Layer

SQLAlchemy ORM with SQLite (swappable to PostgreSQL via DATABASE_URL env var).
Tables: users, app_configs, uploaded_models, prediction_logs
Auto-creates tables and seeds default config + admin on first boot.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, JSON, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import QueuePool, StaticPool

from config import DATABASE_URL, SQLITE_WAL_MODE, IS_PRODUCTION
from logging_config import get_logger

logger = get_logger("database")

# ─── Engine Configuration ─────────────────────────────────────────────────────

_is_sqlite = "sqlite" in DATABASE_URL

# SQLite-specific configuration
_connect_args = {}
_pool_class = QueuePool

if _is_sqlite:
    _connect_args = {"check_same_thread": False}
    _pool_class = StaticPool  # Better for SQLite single-writer

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,  # Verify connections before use (prevents stale connections)
    echo=False
)


# Enable WAL mode for SQLite (better concurrent read performance)
if _is_sqlite and SQLITE_WAL_MODE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


# ─── ORM Models ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    role = Column(String(20), nullable=False, default="USER")  # ADMIN or USER
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    predictions = relationship("PredictionLog", back_populates="user")
    uploaded_models = relationship("UploadedModel", back_populates="uploader")


class AppConfig(Base):
    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False, default="")
    description = Column(Text, default="")
    updated_by = Column(String(255), default="system")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class UploadedModel(Base):
    __tablename__ = "uploaded_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    input_shape = Column(String(100), default="(None, 46, 1)")
    num_classes = Column(Integer, default=7)
    accuracy = Column(Float, nullable=True)
    is_active = Column(Boolean, default=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    uploader = relationship("User", back_populates="uploaded_models")


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_filename = Column(String(255), default="")
    predicted_class = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    probability_distribution = Column(JSON, nullable=True)
    inference_latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    user = relationship("User", back_populates="predictions")


# ─── Database Initialization ─────────────────────────────────────────────────

def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Default configuration seed data
DEFAULT_CONFIGS = [
    {"config_key": "app_name", "config_value": "SentiVox", "description": "Application display name"},
    {"config_key": "max_upload_size_mb", "config_value": "15", "description": "Maximum audio file upload size in MB"},
    {"config_key": "silence_trim_top_db", "config_value": "25", "description": "Silence trimming threshold in dB"},
    {"config_key": "active_model_id", "config_value": "1", "description": "Currently active model ID for inference"},
    {"config_key": "allowed_emotions", "config_value": "happy,sad,angry,surprised,neutral,disgust,fear", "description": "Comma-separated active emotion labels"},
    {"config_key": "sample_rate_hz", "config_value": "16000", "description": "Audio resampling target rate in Hz"},
]


def seed_default_config(db):
    """Insert default config values if the table is empty."""
    existing = db.query(AppConfig).count()
    if existing == 0:
        for cfg in DEFAULT_CONFIGS:
            db.add(AppConfig(**cfg))
        db.commit()
        logger.info("Seeded %d default application config values", len(DEFAULT_CONFIGS))


def seed_default_admin(db):
    """Create default admin account if no users exist."""
    from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_NAME
    from auth import hash_password

    existing = db.query(User).count()
    if existing == 0:
        admin = User(
            email=DEFAULT_ADMIN_EMAIL,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            full_name=DEFAULT_ADMIN_NAME,
            role="ADMIN",
            is_active=True
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded default admin account: %s", DEFAULT_ADMIN_EMAIL)
        if DEFAULT_ADMIN_PASSWORD == "admin123" and IS_PRODUCTION:
            logger.warning(
                "Default admin password is insecure! Set DEFAULT_ADMIN_PASSWORD env var "
                "or change it immediately after first login."
            )


def seed_initial_model(db):
    """Register the existing development model in the database."""
    from config import DEFAULT_MODEL_PATH

    existing = db.query(UploadedModel).count()
    model_path = str(DEFAULT_MODEL_PATH)
    if existing == 0 and os.path.exists(model_path):
        model_record = UploadedModel(
            filename=DEFAULT_MODEL_PATH.name,
            original_name=DEFAULT_MODEL_PATH.name,
            file_path=model_path,
            input_shape="(None, 46, 1)",
            num_classes=7,
            is_active=True,
            uploaded_by=None
        )
        db.add(model_record)
        db.commit()
        logger.info("Registered existing development model: %s", DEFAULT_MODEL_PATH.name)


def init_database():
    """Create all tables and seed default data."""
    logger.info("Initializing database at: %s", DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_config(db)
        seed_default_admin(db)
        seed_initial_model(db)
    except Exception as e:
        db.rollback()
        logger.error("Database initialization failed: %s", str(e), exc_info=True)
        raise
    finally:
        db.close()
    logger.info("Database initialization complete")
