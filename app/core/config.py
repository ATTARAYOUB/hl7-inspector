"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

# Request limits
MAX_MESSAGE_BYTES = int(os.getenv("HL7_MAX_MESSAGE_BYTES", 2_000_000))  # 2 MB
MAX_UPLOAD_BYTES = int(os.getenv("HL7_MAX_UPLOAD_BYTES", 5_000_000))    # 5 MB

# CORS — restrict by default
ALLOWED_ORIGINS = os.getenv(
    "HL7_ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
).split(",")

APP_NAME = "HL7 Inspector"
APP_VERSION = "1.0.0"
DEFAULT_FHIR_VERSION = "R4"