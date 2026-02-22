"""Configuration management for CLARA."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Base directory (project root containing .env)
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from project root so PORT etc. are correct when run from any cwd
load_dotenv(BASE_DIR / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
# Legacy support (fallback to separate keys if single key not provided)
if not SARVAM_API_KEY:
    SARVAM_API_KEY = os.getenv("SARVAM_ASR_API_KEY", "") or os.getenv("SARVAM_TTS_API_KEY", "")
# Sarvam STT language: "unknown" = auto-detect, or "hi", "en", etc. Empty = do not pass (API default).
SARVAM_LANGUAGE_CODE = (os.getenv("SARVAM_LANGUAGE_CODE", "unknown").strip().lower() or None)

# Hardware Configuration
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
MIC_DEVICE_INDEX = int(os.getenv("MIC_DEVICE_INDEX", "0")) if os.getenv("MIC_DEVICE_INDEX") else None
# Audio input device: by name substring (e.g. "ReSpeaker") or explicit index
AUDIO_INPUT_DEVICE_NAME = os.getenv("AUDIO_INPUT_DEVICE_NAME", "").strip() or None
_audio_idx = os.getenv("AUDIO_INPUT_DEVICE_INDEX", "").strip()
AUDIO_INPUT_DEVICE_INDEX = int(_audio_idx) if _audio_idx.isdigit() else None

# Paths
FACES_DB_PATH = os.getenv("FACES_DB_PATH", str(BASE_DIR / "config" / "faces.dat"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "chroma_db"))
UI_CONFIG_PATH = os.getenv("UI_CONFIG_PATH", str(BASE_DIR / "config" / "ui_config.json"))
TEMP_DIR = os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))

# RAG Configuration
RAG_MAX_TOKENS = int(os.getenv("RAG_MAX_TOKENS", "6000"))
RAG_MODEL = os.getenv("RAG_MODEL", "llama-3-8b-8192")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "college_knowledge")
COLLEGE_KNOWLEDGE_PATH = os.getenv("COLLEGE_KNOWLEDGE_PATH", str(BASE_DIR / "college_knowledge.txt"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# State Machine Configuration
INACTIVITY_TIMEOUT = float(os.getenv("INACTIVITY_TIMEOUT", "20.0"))

# Audio Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_VAD_FRAME_MS = int(os.getenv("AUDIO_VAD_FRAME_MS", "20"))  # 10, 20, or 30 for webrtcvad
AUDIO_SILENCE_STOP_MS = int(os.getenv("AUDIO_SILENCE_STOP_MS", "1500"))  # stop after this much silence
AUDIO_SPEECH_TIMEOUT_MS = int(os.getenv("AUDIO_SPEECH_TIMEOUT_MS", "10000"))  # max wait for speech to start
# Record mode: "fixed" = record N seconds (proves capture on PC mic); "vad" = VAD start/stop
AUDIO_RECORD_MODE = (os.getenv("AUDIO_RECORD_MODE", "fixed").strip().lower() or "fixed")
if AUDIO_RECORD_MODE not in ("fixed", "vad"):
    AUDIO_RECORD_MODE = "fixed"
AUDIO_FIXED_RECORD_SECONDS = float(os.getenv("AUDIO_FIXED_RECORD_SECONDS", "4.0"))
AUDIO_SILENT_RMS_THRESHOLD = float(os.getenv("AUDIO_SILENT_RMS_THRESHOLD", "0.001"))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "6969"))
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

# Frontend language display name -> config key (for TARGET_LANGUAGE_CODES)
LANGUAGE_NAME_TO_CODE_KEY = {
    "English": "en",
    "Kannada": "kn",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
}
