"""
Application configuration.

All values are read from environment variables (see .env.example).
Never hardcode secrets or credentials here.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Keep local configuration next to the backend, regardless of the directory
# from which `python run.py` is invoked.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_LOCAL_DATABASE = (_BACKEND_DIR / "xai_loan.db").as_posix()
_DEFAULT_UPLOAD_DIR = (_BACKEND_DIR / "private_uploads").as_posix()


def _env_list(key: str, default: str = "http://localhost:5173") -> list[str]:
    raw = os.environ.get(key, default)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass
class BaseConfig:
    ENV: str = os.environ.get("FLASK_ENV", "development")
    DEBUG: bool = False
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    MYSQL_HOST: str = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT: str = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_USER: str = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.environ.get("MYSQL_DATABASE", "xai_loan_db")

    # A fresh clone previously tried to use an unconfigured local MySQL
    # server, making registration fail with a 500.  Configured deployments
    # still use DATABASE_URL unchanged; local development works immediately.
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", f"sqlite:///{_LOCAL_DATABASE}")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    MODEL_PATH: str = os.environ.get("MODEL_PATH", "../ml/models/saved/model.joblib")
    DOCUMENT_UPLOAD_DIR: str = os.environ.get("DOCUMENT_UPLOAD_DIR", _DEFAULT_UPLOAD_DIR)
    MAX_DOCUMENT_SIZE_BYTES: int = int(os.environ.get("MAX_DOCUMENT_SIZE_BYTES", str(5 * 1024 * 1024)))
    MAX_CONTENT_LENGTH: int = 6 * 1024 * 1024
    AADHAAR_HASH_KEY: str = os.environ.get("AADHAAR_HASH_KEY", "")
    DOCUMENT_TYPE_THRESHOLD: float = float(os.environ.get("DOCUMENT_TYPE_THRESHOLD", "0.65"))
    DOCUMENT_NAME_THRESHOLD: float = float(os.environ.get("DOCUMENT_NAME_THRESHOLD", "88"))
    DOCUMENT_SALARY_TOLERANCE: float = float(os.environ.get("DOCUMENT_SALARY_TOLERANCE", "0.02"))
    DOCUMENT_ANNUAL_TOLERANCE: float = float(os.environ.get("DOCUMENT_ANNUAL_TOLERANCE", "0.20"))

    CORS_ORIGINS: list[str] = field(default_factory=lambda: _env_list("CORS_ORIGINS"))
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/api/auth/google/callback")


@dataclass
class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True


@dataclass
class TestingConfig(BaseConfig):
    DEBUG: bool = True
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


@dataclass
class ProductionConfig(BaseConfig):
    DEBUG: bool = False


_CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return _CONFIGS.get(name, DevelopmentConfig)()
