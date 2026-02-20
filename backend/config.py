"""Configuration management for CLARA."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
# Legacy support (fallback to separate keys if single key not provided)
if not SARVAM_API_KEY:
    SARVAM_API_KEY = os.getenv("SARVAM_ASR_API_KEY", "") or os.getenv("SARVAM_TTS_API_KEY", "")

# Hardware Configuration
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
MIC_DEVICE_INDEX = int(os.getenv("MIC_DEVICE_INDEX", "0")) if os.getenv("MIC_DEVICE_INDEX") else None

# Paths
FACES_DB_PATH = os.getenv("FACES_DB_PATH", str(BASE_DIR / "config" / "faces.dat"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
UI_CONFIG_PATH = os.getenv("UI_CONFIG_PATH", str(BASE_DIR / "config" / "ui_config.json"))
TEMP_DIR = os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))

# RAG Configuration
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "6000"))
RAG_MODEL = os.getenv("RAG_MODEL", "llama-3-8b-8192")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "college_knowledge")

# State Machine Configuration
INACTIVITY_TIMEOUT = float(os.getenv("INACTIVITY_TIMEOUT", "20.0"))

# Audio Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Language Code Mappings (for TTS target_language_code)
TARGET_LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
}
