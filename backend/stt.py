"""Sarvam ASR: WAV bytes -> transcript."""
import io
import logging
from typing import Optional

from config import SARVAM_API_KEY, SARVAM_LANGUAGE_CODE

logger = logging.getLogger(__name__)

# Sarvam ASR model
SARVAM_ASR_MODEL = "saaras:v3"


def wav_to_transcript(wav_bytes: bytes) -> Optional[str]:
    """Send WAV (16 kHz mono preferred) to Sarvam ASR; return transcript or None."""
    if not SARVAM_API_KEY or not wav_bytes:
        logger.warning("STT skipped: no API key or empty WAV (len=%s)", len(wav_bytes) if wav_bytes else 0)
        return None
    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        kwargs = {
            "file": io.BytesIO(wav_bytes),
            "model": SARVAM_ASR_MODEL,
            "mode": "transcribe",
        }
        if SARVAM_LANGUAGE_CODE:
            kwargs["language_code"] = SARVAM_LANGUAGE_CODE
        result = client.speech_to_text.transcribe(**kwargs)
        # Handle multiple response shapes
        text = None
        if result is not None:
            if hasattr(result, "text"):
                text = result.text
            elif isinstance(result, str):
                text = result
            elif isinstance(result, dict):
                text = result.get("text") or result.get("transcript")
        if text is not None and (text or "").strip():
            logger.info("STT result: %r", (text or "").strip()[:200])
            return (text or "").strip()
        logger.warning("STT returned empty (result type=%s, repr=%r)", type(result).__name__, repr(result)[:300])
        return None
    except Exception as e:
        logger.exception("Sarvam STT failed: %s", e)
        return None
