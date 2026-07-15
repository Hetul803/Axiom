# Axiom Runtime

Axiom Runtime is an adaptive-environment research platform: an adaptive intelligence runtime that learns unfamiliar interactive environments by experimenting, constructing an executable world model, inferring goals, and planning without a hand-written integration for every environment.

Run backend: `uvicorn startup.backend.main:app --reload`.
Run frontend: `npm install --prefix startup/frontend && npm run dev --prefix startup/frontend`.
