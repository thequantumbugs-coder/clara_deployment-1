"""CLARA backend - FastAPI app with WebSocket support."""
import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend directory is on path when run as script
_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import (
    GROQ_API_KEY,
    HOST,
    PORT,
    FRONTEND_URL,
    RAG_MODEL,
    RAG_TOP_K,
    SARVAM_API_KEY,
    TARGET_LANGUAGE_CODES,
    LANGUAGE_NAME_TO_CODE_KEY,
)
from greetings import GREETINGS
from rag import get_collection, get_relevant_context
from core.audio_pipeline import record_audio
from stt import wav_to_transcript

logger = logging.getLogger(__name__)


def tts_to_base64(text: str, language_code: str) -> str | None:
    """Convert text to speech via Sarvam; return base64 WAV or None on failure."""
    if not SARVAM_API_KEY or not text:
        return None
    try:
        from sarvamai import SarvamAI
        from sarvamai.play import save as sarvam_save

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        audio = client.text_to_speech.convert(
            text=text,
            model="bulbul:v3",
            target_language_code=language_code,
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            sarvam_save(audio, tmp_path)
            with open(tmp_path, "rb") as rf:
                data = rf.read()
            return base64.b64encode(data).decode("utf-8")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        logger.exception("TTS failed: %s", e)
        return None


async def process_user_text_and_reply(session: dict, text: str, websocket: WebSocket) -> None:
    """Shared flow: RAG context, Groq reply, TTS, send state 5 payload. Assumes text is non-empty."""
    await websocket.send_json({"state": 5, "payload": {"isProcessing": True}})
    lang = session.get("language") or "English"
    lang_code = session.get("language_code") or TARGET_LANGUAGE_CODES["en"]
    context = get_relevant_context(text, top_k=RAG_TOP_K)
    if context.strip():
        logger.info("RAG context: ok (%d chars)", len(context))
    else:
        logger.info("RAG context: empty")
    if context.strip():
        system_prompt = (
            f"You are CLARA, a friendly campus assistant. "
            f"Use ONLY the following college information when it is relevant to the user's question. "
            f"Do not invent or assume college-specific facts; only use what is in the College information below. "
            f"If the answer is not in the context, say you don't have that information. "
            f"Reply only in {lang}. Be concise and helpful.\n\nCollege information:\n{context}"
        )
    else:
        system_prompt = (
            f"You are CLARA, a friendly campus assistant. "
            f"For questions about the college or campus, say you don't have that information if you're unsure. "
            f"Reply only in {lang}. Be concise and helpful."
        )
    reply_text = None
    try:
        if GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=RAG_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            reply_text = (completion.choices[0].message.content or "").strip()
        else:
            reply_text = "I'm sorry, the assistant is not configured."
    except Exception as e:
        logger.exception("Groq failed: %s", e)
        reply_text = None
    if not reply_text:
        if context.strip():
            # RAG fallback: answer from retrieved college context when Groq is unavailable
            intro = "Based on our college information: "
            max_fallback_chars = 600
            trimmed = context.strip()
            if len(trimmed) > max_fallback_chars:
                trimmed = trimmed[: max_fallback_chars - 3].rsplit(maxsplit=1)[0] + "..."
            reply_text = intro + trimmed
        else:
            reply_text = (
                "I'm sorry, I couldn't reach the assistant right now. "
                "Please check your Groq API key in .env and try again."
            )
    user_msg = {"id": f"user-{uuid.uuid4().hex}", "role": "user", "text": text}
    assistant_msg = {"id": f"clara-{uuid.uuid4().hex}", "role": "clara", "text": reply_text}
    session["messages"] = session.get("messages", []) + [user_msg, assistant_msg]
    audio_b64 = tts_to_base64(reply_text, lang_code)
    payload = {
        "messages": [user_msg, assistant_msg],
        "isProcessing": False,
        "isSpeaking": bool(audio_b64),
    }
    if audio_b64:
        payload["audioBase64"] = audio_b64
    else:
        payload["isSpeaking"] = False
        payload["error"] = "Reply is shown but could not be read aloud."
    await websocket.send_json({"state": 5, "payload": payload})


@asynccontextmanager
async def lifespan(app: object):
    """Startup: log RAG collection document count. Shutdown: nothing."""
    try:
        coll = get_collection()
        n = coll.count()
        if n == 0:
            logger.warning(
                "RAG: college_knowledge collection is empty. Run: python -m backend.ingest_college_knowledge"
            )
        else:
            logger.info("RAG: college_knowledge has %s documents.", n)
    except Exception as e:
        logger.warning("RAG: could not check collection: %s", e)
    yield


app = FastAPI(title="CLARA Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178",
        "http://localhost:5179", "http://localhost:5180", "http://localhost:5181", "http://localhost:5182",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175", "http://127.0.0.1:5176", "http://127.0.0.1:5177", "http://127.0.0.1:5178",
        "http://127.0.0.1:5179", "http://127.0.0.1:5180", "http://127.0.0.1:5181", "http://127.0.0.1:5182",
        "http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:8001", "http://localhost:8001", "http://127.0.0.1:8002", "http://localhost:8002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "CLARA"}


@app.get("/health")
def health():
    return {"status": "healthy"}


VALID_LANGUAGES = frozenset(LANGUAGE_NAME_TO_CODE_KEY.keys())


@app.websocket("/ws/clara")
async def websocket_clara(websocket: WebSocket):
    await websocket.accept()
    session = {"language": None, "language_code": None, "messages": [], "cached_greeting_audio": None, "cached_greeting_message": None}
    try:
        # FRONT-Clara-1 expects { state: number, payload?: any }
        # Send initial state so client shows sleep screen (can be overridden by ?state= for E2E)
        await websocket.send_json({"state": 0, "payload": None})
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data) if data else {}
                action = msg.get("action") or msg.get("event")
                if action == "wake":
                    await websocket.send_json({"state": 3, "payload": None})
                elif action == "language_selected":
                    language = msg.get("language")
                    if language in VALID_LANGUAGES:
                        session["language"] = language
                        code_key = LANGUAGE_NAME_TO_CODE_KEY[language]
                        session["language_code"] = TARGET_LANGUAGE_CODES[code_key]
                        try:
                            greeting_text = GREETINGS.get(language, GREETINGS["English"])
                            audio_b64 = tts_to_base64(greeting_text, session["language_code"])
                            if audio_b64:
                                session["cached_greeting_audio"] = audio_b64
                                session["cached_greeting_message"] = {"id": "greeting", "role": "clara", "text": greeting_text}
                        except Exception as e:
                            logger.exception("Preload greeting TTS failed: %s", e)
                    await websocket.send_json({"state": 5, "payload": None})  # Chat after language
                elif action == "conversation_started":
                    lang = session.get("language") or "English"
                    greeting_text = GREETINGS.get(lang, GREETINGS["English"])
                    greeting_message = {"id": "greeting", "role": "clara", "text": greeting_text}
                    audio_b64 = session.get("cached_greeting_audio")
                    if audio_b64 and session.get("cached_greeting_message"):
                        payload = {
                            "messages": [session["cached_greeting_message"]],
                            "isSpeaking": True,
                            "audioBase64": audio_b64,
                        }
                        session["cached_greeting_audio"] = None
                        session["cached_greeting_message"] = None
                        await websocket.send_json({"state": 5, "payload": payload})
                    else:
                        lang_code = session.get("language_code") or TARGET_LANGUAGE_CODES["en"]
                        audio_b64 = tts_to_base64(greeting_text, lang_code)
                        payload = {
                            "messages": [greeting_message],
                            "isSpeaking": bool(audio_b64),
                        }
                        if audio_b64:
                            payload["audioBase64"] = audio_b64
                        else:
                            payload["isSpeaking"] = False
                            payload["error"] = "Could not generate greeting audio."
                        await websocket.send_json({"state": 5, "payload": payload})
                elif action == "user_message":
                    text = (msg.get("text") or "").strip()
                    if not text:
                        await websocket.send_json({
                            "state": 5,
                            "payload": {"error": "Missing text", "isProcessing": False},
                        })
                    else:
                        await process_user_text_and_reply(session, text, websocket)
                elif action in ("toggle_mic", "mic_start"):
                    await websocket.send_json({"state": 5, "payload": {"isProcessing": True}})
                    wav_bytes = None
                    try:
                        wav_bytes = await asyncio.to_thread(record_audio)
                    except Exception as e:
                        logger.exception("Backend recording failed: %s", e)
                    if not wav_bytes:
                        await websocket.send_json({
                            "state": 5,
                            "payload": {
                                "error": "No speech heard.",
                                "errorCode": "MIC_CAPTURE_FAILED",
                                "isProcessing": False,
                            },
                        })
                    else:
                        transcript = wav_to_transcript(wav_bytes)
                        if not (transcript or "").strip():
                            logger.warning("STT returned empty for %d-byte WAV; check backend STT logs and mic device.", len(wav_bytes))
                            await websocket.send_json({
                                "state": 5,
                                "payload": {
                                    "error": "No speech detected.",
                                    "errorCode": "NO_SPEECH_DETECTED",
                                    "isProcessing": False,
                                },
                            })
                        else:
                            await process_user_text_and_reply(session, transcript.strip(), websocket)
                elif action in ("mic_stop", "mic_cancel"):
                    # No-op for now; cancel would require a shared flag checked inside record_audio
                    await websocket.send_json({"state": 5, "payload": {"isProcessing": False}})
                elif action == "menu_select":
                    await websocket.send_json({"state": 5, "payload": msg})
                else:
                    await websocket.send_json({"state": 5, "payload": msg})
            except Exception:
                await websocket.send_json({"state": 0, "payload": None})
    except Exception as e:
        try:
            await websocket.send_json({"state": -1, "payload": {"error": str(e)}})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    logger.info("Groq API key: %s", "loaded" if GROQ_API_KEY else "not set (check .env)")
    logger.info("WebSocket: ws://localhost:%s/ws/clara — frontend VITE_WS_URL must match this", PORT)
    uvicorn.run(app, host=HOST, port=PORT)
