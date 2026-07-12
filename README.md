# Avishkara

AI-powered sports talent discovery through physics-informed biomechanics
analysis for running, jumping, and cricket fast bowling.

## Confirmed stack

- Next.js 15 App Router, TypeScript, Tailwind CSS, and shadcn/ui
- FastAPI and Python
- PostgreSQL through Supabase
- MediaPipe Pose and OpenCV

## Processing architecture

```text
Frontend
  -> FastAPI
  -> MediaPipe Pose
  -> Biomechanics Engine
  -> Benchmark Engine
  -> Dashboard
```

## Current milestone

The first milestone implements a transparent vertical-jump analyzer. It accepts
time-series pose landmarks, detects take-off and landing, and reports flight
time, jump height, joint angles, symmetry, landing stability, and an explainable
score. A pretrained pose detector will supply these landmarks from video in the
next milestone.

## Run the API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Test

```powershell
cd backend
pytest
```

## Design principle

Pose estimation measures body-joint locations. Avishkara's own deterministic
physics engine calculates the biomechanics metrics and score. No LLM is used in
the product.
