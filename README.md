# CLARA – AI Receptionist Kiosk System

Full-stack application: **React (Vite)** frontend + **FastAPI** backend with WebSocket for the CLARA AI receptionist kiosk.

**Repository:** [FB-Clara](https://github.com/thequantumbugs-coder/FB-Clara)

## Repository structure

```
├── backend/          # FastAPI API + WebSocket (/ws/clara)
├── frontend/         # React 19 + Vite + TypeScript UI
├── config/           # UI config, college knowledge
├── run.sh            # Run backend only
├── run-both.sh       # Run backend + frontend
└── .env.example      # Backend env template (copy to .env)
```

## Prerequisites

- **Node.js** 20+ (for frontend)
- **Python** 3.8+ (for backend)

## Clone and setup

```bash
git clone https://github.com/thequantumbugs-coder/FB-Clara.git
cd FB-Clara
```

Then run with one of the options below. On systems without Node in `PATH`, you can extract a Node binary into `.node/` (see frontend README); `run-both.sh` will use `.node/bin` if present.

## Quick start

### Option 1: Run both (backend + frontend)

```bash
./run-both.sh
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173  

### Option 2: Run separately

Start the **backend first**, then the frontend. The frontend connects to the backend WebSocket (default `ws://localhost:8001/ws/clara`; override with `VITE_WS_URL` in `frontend/.env.local`) and retries every 3 seconds if the backend is not running. If the backend reports "address already in use", free the port (e.g. `netstat -ano | findstr :8001` then `taskkill /PID <pid> /F`) or set `PORT=8002` in `.env` and `VITE_WS_URL=ws://localhost:8002/ws/clara` in `frontend/.env.local`.

**Backend**

```bash
./run.sh
# → http://localhost:8000 (or PORT from .env, e.g. 8001)
```

**Frontend** (in another terminal)

```bash
cd frontend && npm install && npm run dev
# → http://localhost:5173 (or next available port if 5173 is in use)
```

## Configuration

- Copy `.env.example` to `.env` in the project root and set API keys (e.g. `GROQ_API_KEY`, `SARVAM_*`) if you use backend features that need them.
- **College knowledge (RAG):** To let Clara answer from `college_knowledge.txt`, run once: `python -m backend.ingest_college_knowledge`. See BASELINE.md for details.
- Frontend: optional `frontend/.env.local` (e.g. `GEMINI_API_KEY`, `VITE_WS_URL` for a different backend WebSocket URL such as `ws://localhost:8002/ws/clara`).

### Voice / TTS (CLARA speaks in your language)

For full voice (greeting and replies spoken in the selected language), set in `.env`:

- `GROQ_API_KEY` – for LLM replies (e.g. from [Groq Console](https://console.groq.com/keys)).
- `SARVAM_API_KEY` – for text-to-speech (or `SARVAM_ASR_API_KEY` / `SARVAM_TTS_API_KEY`; get keys at [Sarvam AI](https://dashboard.sarvam.ai/)).

Run the backend with **full** dependencies (not minimal): `pip install -r backend/requirements.txt`. Supported languages: English, Kannada, Hindi, Tamil, Telugu, Malayalam. The frontend sends the selected language with `language_selected`; user speech is sent as `user_message` with `text` (from the browser’s speech recognition).

## Tech stack

| Layer    | Stack |
| -------- | ----- |
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS, Motion |
| Backend  | FastAPI, Uvicorn, WebSockets |
| Protocol | WebSocket at `ws://localhost:8000/ws/clara` (state + payload) |

## Pushing to GitHub (FB-Clara)

This repo is set up to push to **https://github.com/thequantumbugs-coder/FB-Clara**. From the project root:

```bash
./push-to-fb-clara.sh
```

If Git prompts for credentials, use your GitHub username and a [Personal Access Token](https://github.com/settings/tokens) (scope `repo`). Or use SSH: `git remote set-url fb-clara git@github.com:thequantumbugs-coder/FB-Clara.git` then run the script again.

## Development

- Backend: `backend/main.py` (FastAPI), `backend/config.py` (env from `.env`).
- Frontend: `frontend/` (Vite + React); WebSocket URL in `frontend/src/App.tsx` (`ws://localhost:8000/ws/clara`).

## License

See repository defaults.
