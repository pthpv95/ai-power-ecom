# AI-powered E-commerce Platform

A modern e-commerce platform with an AI-driven shopping assistant.

## Project Structure

- `backend/`: FastAPI application with PostgreSQL and Pinecone integration.
- `frontend/`: React application built with Vite and Tailwind CSS.
- `docker-compose.yml`: Docker configuration for local development.

## Tech Stack

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** PostgreSQL with [SQLAlchemy](https://www.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/)
- **Vector Search:** [Pinecone](https://www.pinecone.io/)
- **AI Integration:** [OpenAI SDK](https://github.com/openai/openai-python)
- **Package Manager:** [uv](https://github.com/astral-sh/uv)

### Frontend
- **Framework:** [React 19](https://react.dev/)
- **Build Tool:** [Vite](https://vitejs.dev/)
- **Styling:** [Tailwind CSS 4](https://tailwindcss.com/)
- **Language:** [TypeScript](https://www.typescriptlang.org/)

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

### Setup

1. **Backend:**
   ```bash
   cd backend
   uv sync
   # Set up .env file
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   # Set up .env file
   ```

3. **Docker:**
   ```bash
   docker-compose up -d
   ```

## License

MIT
