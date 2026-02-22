# CLARA Kiosk — Baseline (Original / Current Structure)

This document captures the **baseline** state of the project: structure, voice integration (Groq + Sarvam), RAG (college knowledge), backend/frontend connection, and how to run it. All E2E tests in `frontend/e2e/chat-flow.spec.ts` define accepted behavior.

**Date:** 2026-02-21

**Summary of this baseline:** Single default port 6969 (backend + frontend fallback + .env.example). Backend started via `start-backend.ps1` (Windows) or `run-both.sh` (Bash); frontend after. Connection banner with /health and restart-frontend hint. user_message flow: RAG first, then Groq; if Groq fails, reply is RAG fallback text or generic error. RAG can return empty (empty collection, ChromaDB error, or language mismatch). Groq optional for now; RAG fallback shows college info when context is non-empty.

---

## Revert to original

**When you say "revert to original"** you mean: bring the project back to **this** state.

- Restore code and config to match this baseline (same backend actions, same frontend flow, same files listed below).
- Run instructions: use the "How to run" section.
- Voice: greeting TTS and reply TTS in the selected language (Groq + Sarvam) when `.env` has valid keys.

---

## Application flow

| Step | State | Screen | Transition |
|------|--------|--------|-------------|
| 1 | 0 | **Sleep** | Tap → state 3 |
| 2 | 3 | **Language Select** | Select language → state 5 (language sent to backend) |
| 3 | 5 | **Chat** | Back → state 3 |

- **Voice:** On entering chat, frontend sends `conversation_started`; backend returns greeting message + TTS audio (Sarvam). User taps orb → browser speech recognition → transcript sent as `user_message` → backend uses Groq for reply, Sarvam for TTS, returns reply + audio. All in the selected language (English, Kannada, Hindi, Tamil, Telugu, Malayalam).

---

## Backend (current structure)

- **Entry:** `backend/main.py` (FastAPI + WebSocket).
- **Config:** `backend/config.py` — env from `.env`; `TARGET_LANGUAGE_CODES`, `LANGUAGE_NAME_TO_CODE_KEY`, `GROQ_API_KEY`, `SARVAM_API_KEY`, `RAG_MODEL`.
- **Greetings:** `backend/greetings.py` — `GREETINGS` dict (six languages, same text as frontend `claraGreeting`).
- **Dependencies (voice):** `backend/requirements-voice.txt` (fastapi, uvicorn, websockets, pydantic, python-dotenv, groq, sarvamai). Full stack: `backend/requirements.txt`.

**WebSocket:** Backend listens on `PORT` from `.env` (default in `config.py` is 6969). Frontend uses `VITE_WS_URL` from `frontend/.env.local` (e.g. `ws://localhost:6969/ws/clara`); fallback in code is `ws://localhost:6969/ws/clara`. **Backend and frontend ports must match** — same number in `PORT` and in the host part of `VITE_WS_URL`. At startup the backend logs: `WebSocket: ws://localhost:<PORT>/ws/clara — frontend VITE_WS_URL must match this`.

**Actions (frontend → backend):**

| action | payload | purpose |
|--------|--------|---------|
| `wake` | — | → state 3 |
| `language_selected` | `language: string` | Store session language; preload greeting TTS (cache); → state 5 |
| `conversation_started` | — | Send cached greeting audio if present, else generate TTS; → state 5, payload: messages + audioBase64 + isSpeaking |
| `toggle_mic` | — | (optional) |
| `user_message` | `text: string` | RAG retrieval first, then Groq reply + Sarvam TTS; → state 5, payload: messages + audioBase64 + isSpeaking. If Groq fails and RAG returned context, reply is "Based on our college information: " + context; otherwise generic error message. |

**Backend → frontend payload:** `messages`, `isListening`, `isProcessing`, `isSpeaking`, `audioBase64`, `error` (optional).

**Scripts:**
- **`start-backend.ps1`** (Windows): Run from project root. Reads `PORT` from `.env` (default 6969), frees that port if in use (kills process by PID), then starts backend with `.venv\Scripts\python.exe backend\main.py`. Do not use `$pid` as a variable (PowerShell reserved); script uses `$procId`.
- **`run-both.sh`** (Bash): Reads `PORT` from `.env`, exports it, starts backend in background then frontend. Use on WSL/macOS/Linux.

---

## Frontend (current structure)

```
frontend/
├── e2e/
│   └── chat-flow.spec.ts
├── src/
│   ├── App.tsx                 # State 0, 3, 4|5; sends language in language_selected; passes payload to ChatScreen
│   ├── main.tsx
│   ├── index.css
│   ├── context/
│   │   └── LanguageContext.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useVoiceAnalyser.ts
│   │   └── useSpeechRecognition.ts   # Tap orb → Speech Recognition → user_message with text
│   ├── types/
│   │   └── chat.ts
│   └── components/
│       ├── SleepScreen.tsx
│       ├── LanguageSelect.tsx       # onSelect(language: Language) → parent sends language
│       ├── ChatScreen.tsx            # Plays payload.audioBase64; effectiveSpeaking; greeting + merge messages
│       ├── VoiceOrbCanvas.tsx
│       ├── VoiceOrb.tsx
│       ├── VoiceConversation.tsx
│       └── chat/
│           ├── ClaraBubble.tsx
│           ├── UserBubble.tsx
│           ├── CardMessage.tsx
│           ├── CollegeDiaryCard.tsx
│           └── ImageCard.tsx
```

---

## Environment and run

**Run order:** (1) Start the **backend first** from `clara_deployment-1`. (2) Then start the **frontend**. The frontend connects using `VITE_WS_URL` (or fallback `ws://localhost:6969/ws/clara`) and retries every few seconds. If the backend is not up, a banner appears with start commands, a link to `/health`, and a note to restart the frontend if `frontend/.env.local` was changed.

**Copy-paste commands (Windows, from project root):**
- **Terminal 1 — backend:**  
  `cd "c:\Users\aashu\OneDrive\Desktop\DEP CLARA-1\clara_deployment-1"`  
  `.\start-backend.ps1`  
  (Or: `.\.venv\Scripts\python.exe backend\main.py`)
- **Terminal 2 — frontend:**  
  `cd "c:\Users\aashu\OneDrive\Desktop\DEP CLARA-1\clara_deployment-1\frontend"`  
  `npm run dev`  
  Then open the URL Vite prints (e.g. http://localhost:5176).
- **Verify backend:** Open `http://localhost:6969/health` in browser; expect `{"status":"healthy"}`.

- **`.env`** (project root `clara_deployment-1`, gitignored): copy from `.env.example`. Set `GROQ_API_KEY`, `SARVAM_API_KEY`, and `PORT` (e.g. `6969`). Missing keys can cause TTS or Groq to fail; the UI may show "Couldn't reach the assistant" or similar. **After changing `GROQ_API_KEY` or any `.env` value, restart the backend** so the new values are loaded (env is read only at process start).
- **Port already in use (Windows):** Run `netstat -ano | findstr ":6969"` (or your `PORT`). The **last column** is the process ID (PID), not the port. Then `Stop-Process -Id <PID> -Force`. Or use `.\start-backend.ps1`, which frees the port and starts the backend. Alternatively change `PORT` in `.env` and set `VITE_WS_URL=ws://localhost:<new port>/ws/clara` in `frontend/.env.local`, then restart both.
- **Frontend still shows "Cannot connect to backend":** Restart the frontend (`npm run dev`) after changing `frontend/.env.local` so Vite picks up `VITE_WS_URL`. Check backend is running by opening `http://localhost:<PORT>/health`.
- **Backend (voice):** From `clara_deployment-1`:  
  `python -m venv .venv` (if needed)  
  `.venv\Scripts\pip install -r backend\requirements.txt` (or `requirements-voice.txt`)  
  `.venv\Scripts\python backend\main.py` (or `.\start-backend.ps1` on Windows)  
  → Confirm log shows "Uvicorn running on http://0.0.0.0:<PORT>" (e.g. 6969). Check "Groq API key: loaded" to confirm the key was read.
- **Frontend:** From `clara_deployment-1\frontend`:  
  `npm install` (or `npm ci` if lockfile clean)  
  `npm run dev`  
  → Open the URL Vite prints (e.g. http://localhost:5176). If Vite uses a different port, use that URL.
- **E2E:** With backend and frontend running: `cd frontend && npx playwright test e2e/chat-flow.spec.ts --project=chromium`

---

## College knowledge (RAG)

Clara answers using relevant parts of `college_knowledge.txt`. The file is chunked and embedded into ChromaDB; at query time the backend retrieves the top-k chunks and injects them into the LLM prompt.

**user_message flow (backend):** (1) **RAG first:** `get_relevant_context(text)` returns context (or empty string if collection empty, query fails, or ChromaDB errors). (2) **Groq:** System prompt includes context when non-empty; LLM reply is `reply_text`. (3) **If Groq fails or no API key:** If `reply_text` is empty, fallback = "Based on our college information: " + trimmed context when context is non-empty; otherwise the user sees "I'm sorry, I couldn't reach the assistant right now. Please check your Groq API key in .env and try again." So **RAG is always run**; if RAG returns empty (ChromaDB/collection issue), and Groq also fails, the user gets the generic error instead of college content.

- **Run ingestion once** after cloning or when you update `college_knowledge.txt`:
  - From project root: `python -m backend.ingest_college_knowledge`
  - Or from `backend/`: `python ingest_college_knowledge.py`
  - Use **Python 3.10–3.12** for ingestion (ChromaDB may fail on Python 3.14+). If needed: `py -3.12 -m venv .venv312`, then `.venv312\Scripts\pip install -r backend/requirements.txt`, then `.venv312\Scripts\python -m backend.ingest_college_knowledge`.
- **Config (optional):** In `.env` you can set `COLLEGE_KNOWLEDGE_PATH` (default: `college_knowledge.txt` at project root), `CHROMA_DB_PATH` (default: `./chroma_db`), `CHROMA_COLLECTION_NAME` (default: `college_knowledge`), and `RAG_TOP_K` (default: 5 chunks per query). The ChromaDB directory is gitignored.
- **Verify college Q&A:** After starting backend and frontend, ask Clara e.g. "Where is SVIT located?" or "What is the CSE intake?" and confirm the answer matches `college_knowledge.txt`. If the backend logs "RAG: college_knowledge collection is empty" at startup, run the ingestion command above first.
- **RAG returning empty:** If you see "check your Groq API key" even when you expect college info, RAG context is empty. Check backend logs for "RAG context: ok (N chars)" vs "RAG context: empty". Causes: (1) Collection empty — run ingestion. (2) ChromaDB error at startup (e.g. "could not check collection: unable to infer type...") — use Python 3.10–3.12 for backend/ingestion or fix ChromaDB. (3) Query language (e.g. Kannada) may not match English chunks well with default embeddings.

---

## Audio (input / output)

- **Voice input** requires a browser that supports the Web Speech API (Chrome or Edge recommended). If the browser does not support it or the user denies the microphone, a short message is shown (e.g. "Voice input is not supported. Please use Chrome or Edge." or "Microphone access denied."). The user can tap again to retry; the message auto-clears after a few seconds.
- **Greeting delay:** The greeting TTS is preloaded when the user selects a language (`language_selected`). When they reach chat (`conversation_started`), the cached audio is sent immediately so there is no 2–4s wait. If preload failed, the backend falls back to generating TTS on `conversation_started` and may show "Could not generate greeting audio." if TTS fails.
- **Tap guard:** The mic is not started while backend audio is playing or the backend has set `isProcessing`. Tap is only active when the orb is idle or off and not playing/processing.
- **Errors:** If TTS fails for a reply, the text is still shown and a short note like "Reply is shown but could not be read aloud." may appear. Playback errors clear the speaking state so the orb does not get stuck.

---

## Baseline test cases

1. **Sleep → Language → Chat** — Wake, select English, assert Chat screen with CLARA header, greeting text, voice orb.
2. **URL ?state=5** — Direct load to chat; assert chat screen, greeting, orb.
3. **Debug keys 3 then 5** — Key 3 → language; key 5 → chat; assert chat visible.

---

## Key files (original state checklist)

| Path | Purpose |
|------|--------|
| `backend/main.py` | WebSocket handler; session (cached_greeting_audio); language_selected (preload TTS); conversation_started (cache or fallback); user_message: RAG → Groq → fallback ("Based on our college information" or Groq error); tts_to_base64; startup log WebSocket URL |
| `backend/config.py` | PORT (default 6969), TARGET_LANGUAGE_CODES, LANGUAGE_NAME_TO_CODE_KEY, GROQ/SARVAM, RAG_*, CHROMA_* |
| `backend/rag.py` | get_collection, get_relevant_context; returns "" on error or empty collection |
| `backend/greetings.py` | GREETINGS by language |
| `backend/requirements-voice.txt` | Voice-only deps |
| `start-backend.ps1` | Windows: read PORT from .env, free port ($procId), start backend |
| `run-both.sh` | Bash: read PORT from .env, start backend then frontend |
| `frontend/src/App.tsx` | WS_URL fallback 6969; connection banner with start commands, /health link, restart frontend hint |
| `frontend/src/hooks/useWebSocket.ts` | Retry on disconnect; dev console hint when connection fails |
| `frontend/src/components/LanguageSelect.tsx` | onSelect(language: Language) |
| `frontend/src/components/ChatScreen.tsx` | payload.audioBase64 playback; isPlayingBackendAudio; effectiveSpeaking; recognitionError + payload error; tap guard |
| `frontend/src/hooks/useSpeechRecognition.ts` | startListening → user_message with transcript; onError; double-start guard |
| `.env.example` | Env template; PORT=6969 |
| `frontend/.env.local` | VITE_WS_URL=ws://localhost:6969/ws/clara (match PORT) |

---

*Baseline = this state. "Revert to original" means restore to this baseline.*
