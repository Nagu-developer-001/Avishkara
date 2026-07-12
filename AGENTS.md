# Avishkara Development Guide

## Product

Avishkara is an AI-powered sports talent discovery platform supporting running,
jumping, and cricket bowling.

## Technology

- Next.js 15 with the App Router
- TypeScript
- Tailwind CSS
- shadcn/ui
- FastAPI with Python
- PostgreSQL through Supabase
- MediaPipe Pose
- OpenCV

## Architecture

Frontend -> FastAPI -> MediaPipe Pose -> Biomechanics Engine -> Benchmark Engine
-> Dashboard

Keep these boundaries explicit:

- The frontend handles presentation, capture/upload, and API interaction.
- FastAPI validates requests and coordinates analysis.
- MediaPipe Pose extracts landmarks from video.
- The biomechanics engine calculates explainable physical metrics.
- The benchmark engine converts metrics into sport-specific assessments.
- The dashboard presents results without duplicating scoring logic.

## Engineering Rules

- Use clean architecture and modular boundaries.
- Build reusable components.
- Use TypeScript for all frontend code.
- Do not add features unless requested.
- Avoid unnecessary comments; prefer clear names and small functions.
- Explain intended file changes before editing code.
- Keep biomechanics calculations deterministic and testable.
- Do not use an LLM in the product unless explicitly requested as a last resort.
