# CLARA – AI Receptionist Kiosk System

Full-stack application: **React (Vite)** frontend + **FastAPI** backend with WebSocket for the CLARA AI receptionist kiosk.

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

## Quick start

### Option 1: Run both (backend + frontend)

```bash
./run-both.sh
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173  

### Option 2: Run separately

**Backend**

```bash
./run.sh
# → http://localhost:8000 (API + WebSocket)
```

**Frontend** (in another terminal)

```bash
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

## Configuration

- Copy `.env.example` to `.env` in the project root and set API keys (e.g. `GROQ_API_KEY`, `SARVAM_*`) if you use backend features that need them.
- Frontend: optional `frontend/.env.local` (e.g. `GEMINI_API_KEY`, `VITE_WS_URL`) for the React app.

## Tech stack

| Layer    | Stack |
| -------- | ----- |
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS, Motion |
| Backend  | FastAPI, Uvicorn, WebSockets |
| Protocol | WebSocket at `ws://localhost:8000/ws/clara` (state + payload) |

## License

See repository defaults.
