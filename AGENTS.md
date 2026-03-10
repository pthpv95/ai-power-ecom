# Repository Guidelines

## Project Structure & Module Organization
This repository is split into `backend/` and `frontend/`. FastAPI code lives in `backend/app/`, with routes in `backend/app/api/`, agent logic in `backend/app/agent/`, services in `backend/app/services/`, migrations in `backend/alembic/versions/`, and tests in `backend/tests/`. React code lives in `frontend/src/`, with components in `frontend/src/components/`, API helpers in `frontend/src/api/`, assets in `frontend/public/` or `frontend/src/assets/`, and Playwright specs in `frontend/tests/`. Longer design notes live in `docs/` and `openspec/`.

## Build, Test, and Development Commands
Backend uses `uv`; frontend uses `npm`.

- `cd backend && uv sync`: install Python dependencies.
- `cd backend && uv run uvicorn app.main:app --reload`: start the API on port 8000.
- `cd backend && uv run arq app.worker.WorkerSettings`: start the background worker.
- `cd backend && uv run pytest`: run backend tests.
- `cd backend && uv run alembic upgrade head`: apply database migrations.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: start the Vite dev server on port 5173.
- `cd frontend && npm run build`: type-check and build production assets.
- `cd frontend && npm run lint`: run ESLint for `ts`/`tsx` files.
- `cd frontend && npm run test:e2e`: run Playwright tests; backend must already be running.

## Coding Style & Naming Conventions
Follow existing style: Python uses 4-space indentation, type-aware FastAPI modules, and snake_case filenames such as `context_manager.py`. TypeScript/React uses 2-space indentation, PascalCase component files such as `ProductGrid.tsx`, and camelCase for functions and props. Frontend linting is defined in `frontend/eslint.config.js`; no separate formatter is configured, so match surrounding code closely.

## Testing Guidelines
Backend tests use `pytest` with `pytest-asyncio`; place new tests in `backend/tests/` as `test_<feature>.py`. Frontend coverage is E2E-first through Playwright; add specs in `frontend/tests/` with `*.spec.ts`. For UI changes, cover user-facing flows.

## Commit & Pull Request Guidelines
Recent history follows short imperative commits, usually Conventional Commit style, for example `feat: replace hardcoded user_abc with guest identity system` or `docs: add implementation details`. Keep commits scoped and descriptive. PRs should include a concise summary, linked issue or spec when relevant, migration or env-var notes for backend changes, and screenshots for visible frontend changes. Include the commands you ran to verify the change.

## Security & Configuration Tips
Do not commit `.env` files or secrets. Backend features depend on PostgreSQL, Redis, OpenAI, and Pinecone configuration, so document any new required variables when adding integrations.
