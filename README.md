# ConsistencyAI

Production application foundation for ConsistencyAI.

## Product
ConsistencyAI is a personal consistency system for everyday life. Users define what matters to them, create Life Rules, plan their days, complete interactive check-ins, and receive AI-generated daily, weekly, and monthly insights.

## Architecture
- Frontend: React + TypeScript + Vite
- Backend: Flask + SQLAlchemy + Pydantic
- Database: MySQL
- Authentication: JWT-ready service boundary
- AI: provider-independent service boundary
- Testing: Pytest backend + Vitest-ready frontend

## Development
1. Copy `.env.example` to `.env`.
2. Create the backend virtual environment and install `backend/requirements.txt`.
3. Install frontend dependencies with `npm install`.
4. Run the Flask API and Vite frontend separately.

The prototype is intentionally not used as production application logic. Its UX decisions are the reference for the new implementation.

## Implemented production phase 2
- JWT authentication with password hashing.
- Goals API.
- Life Rules API.
- Daily Tasks API with completion updates.
- Daily Check-in API with task completion aggregation.
- Provider-independent AI service boundary.
- MySQL migrations for the consistency domain.
- Authentication test coverage.

## Security note
JWT secret, application secret and database credentials are environment configuration. Never commit `.env`.
