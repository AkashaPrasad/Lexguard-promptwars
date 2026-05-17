"""Application configuration loaded from environment variables."""
import os
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Google Cloud
GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_FLASH: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL_PRO: str = os.getenv("GEMINI_MODEL_PRO", "gemini-2.5-flash")
DOCUMENT_AI_PROCESSOR_ID: str = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "lexguard-documents")
FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")

# App Settings
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CONTRACT_TEXT_BYTES: int = 500 * 1024  # 500KB
ALLOWED_MIME_TYPES: List[str] = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/png",
    "image/jpeg",
]
ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"]
RATE_LIMIT_REQUESTS: int = 10
RATE_LIMIT_WINDOW_SECONDS: int = 3600
APP_VERSION: str = "1.0.0"

# CORS
CORS_ORIGINS: List[str] = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

# Risk Severity Thresholds
RISK_CRITICAL_MIN: int = 8
RISK_HIGH_MIN: int = 6
RISK_MEDIUM_MIN: int = 4
RISK_LOW_MIN: int = 1
