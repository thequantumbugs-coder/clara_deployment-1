#!/bin/bash
# Run CLARA backend (API + WebSocket at http://localhost:8000).
# Frontend: cd frontend && npm install && npm run dev → http://localhost:5173
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r backend/requirements-minimal.txt
fi
echo "Starting CLARA backend at http://localhost:8000"
exec .venv/bin/python backend/main.py
