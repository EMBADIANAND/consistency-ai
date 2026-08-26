# 🚀 ConsistencyAI

**ConsistencyAI** is a full-stack consistency tracker. You plan a few honest intentions for the day, keep the promises you have made to yourself, and the app turns that history into streaks, weekly patterns and coaching — all computed from your own data, never invented.

> One Flask process serves the JSON API and the built React app, so the whole product is a single container.

---

## ✨ What it does

| Screen | What it actually does |
| --- | --- |
| **Home** | Today's real tasks, live completion rate and streak; tick things off in place |
| **Plan** | Build or edit any day's plan, pull in life rules, move between days |
| **Rules** | Create life rules, mark them kept, watch per-rule streaks build |
| **Review** | End-of-day check-in with mood and reflection, answered by an AI insight |
| **Reports** | Weekly consistency, day-by-day chart, per-rule breakdown, detected patterns |
| **Coach** | A real conversation that remembers the thread and survives a reload; replies stream in and are grounded in your own numbers |
| **Journey** | 30-day consistency score, longest streak, earned identity traits, account |

Everything is scoped to the signed-in user — every query filters by the id inside the JWT, never by anything the client sends.

---

## 🛠️ Tech

**Frontend** React 19 · TypeScript · Vite · hand-rolled API client and auth context (no state library)
**Backend** Flask 3 · SQLAlchemy 2 · pydantic v2 · PyJWT · gunicorn
**Database** SQLite for development · MySQL or PostgreSQL in production
**AI** Pluggable provider behind one interface: a deterministic rule engine by default, Claude when a key is present

---

## ⚙️ Run it locally

### Option A — Docker (closest to production)

```bash
cp .env.example .env          # then set SECRET_KEY and JWT_SECRET_KEY
docker compose up --build
```

Open <http://localhost:8000>. The app and a MySQL 8 database come up together.

### Option B — the two dev servers

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main               # http://127.0.0.1:5000
```

**Frontend** (new terminal)

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

The Vite dev server proxies `/api` to Flask, so the SPA calls the same paths in development and production.

### Load a demo account

```bash
cd backend
FLASK_APP=app flask seed         # Windows: set FLASK_APP=app && flask seed
```

That creates `demo@consistency.ai` / `demo-password-123` with 45 days of history, so every screen has something real to show.

---

## 🧪 Tests

```bash
cd backend && PYTHONPATH=. python -m pytest -q     # API, auth, streaks, ownership
cd frontend && npm test                            # API client, date handling
cd frontend && npm run build                       # type-check + production build
```

CI runs all three plus a Docker build on every push (`.github/workflows/ci.yml`).

---

## 📡 API

All routes live under `/api/v1`. Everything except `/health`, `/auth/register` and `/auth/login` needs `Authorization: Bearer <token>`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness plus a real database round trip |
| `POST` | `/auth/register` | Create an account, returns a token and the user |
| `POST` | `/auth/login` | Sign in |
| `GET` | `/auth/me` | The signed-in account |
| `GET` | `/summary/today` | Today's counts, completion rate, streak, greeting |
| `GET` | `/daily-tasks?date=` | Tasks for a day (or `from`/`to` for a range) |
| `POST` | `/daily-tasks` | Add one task |
| `PUT` | `/daily-tasks/plan` | Replace a day's plan, preserving completions |
| `PATCH` | `/daily-tasks/{id}/completion` | Tick or untick |
| `DELETE` | `/daily-tasks/{id}` | Remove a task |
| `GET` | `/life-rules?date=` | Rules with streak and today's state |
| `POST` | `/life-rules` | Create a rule |
| `PATCH` | `/life-rules/{id}` | Edit a rule |
| `DELETE` | `/life-rules/{id}` | Archive a rule (history is kept) |
| `POST` | `/life-rules/{id}/complete?date=` | Toggle "kept" for a day |
| `GET` | `/check-ins` · `/check-ins/{date}` | Recent check-ins · one day |
| `POST` | `/check-ins` | Save the day's check-in, returns an AI reflection |
| `GET` | `/reports/weekly` | This week vs last, per-day chart data, patterns |
| `GET` | `/journey` | 30-day score, streaks, identity traits |
| `GET` | `/coach/prompt` | The opening "I noticed something" card |
| `GET` | `/coach/conversation` | The open thread and its messages |
| `POST` | `/coach/chat` | Send a turn; the reply streams back as server-sent events |
| `POST` | `/coach/conversation/reset` | Close the thread (nothing is deleted) |
| `POST` | `/coach/ask` | One-shot question, no memory (superseded by `/coach/chat`) |
| `GET`/`POST`/`PATCH`/`DELETE` | `/goals…` | Long-horizon goals |

Example:

```http
POST /api/v1/auth/register
Content-Type: application/json

{"display_name": "Anand", "email": "anand@example.com", "password": "StrongPass123"}
```

---

## 🚢 Deploy

The image is self-contained: it builds the frontend, installs the backend and serves both from `gunicorn` on `$PORT`.

**Render** — push the repo, then create a Blueprint from `render.yaml`. It provisions a free PostgreSQL instance, generates `SECRET_KEY` and `JWT_SECRET_KEY`, wires `DATABASE_URL` in and health-checks `/api/v1/health`.

**Anywhere else that runs a container** (Railway, Fly.io, Cloud Run, a VPS):

```bash
docker build -t consistency-ai .
docker run -p 8000:8000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  -e JWT_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  -e DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/consistency_ai" \
  consistency-ai
```

`postgres://` and `mysql://` URLs are rewritten to the drivers SQLAlchemy 2 expects, so a provider-supplied `DATABASE_URL` works unedited.

### Configuration

Every setting is an environment variable — see `.env.example`. The ones that matter in production:

| Variable | Why |
| --- | --- |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Must be real, distinct secrets. The app logs an error at boot if they are still placeholders. |
| `DATABASE_URL` | Point at a managed database; the SQLite default does not survive a container restart. |
| `CORS_ORIGINS` | Only needed if the SPA is served from a different origin than the API. |
| `AI_PROVIDER` | `mock` (default, no key) or `anthropic` with `ANTHROPIC_API_KEY`. |
| `AI_DAILY_LIMIT` | AI-answered requests per account per day (default 100). The only thing between a looping client and your whole API budget. `0` disables it. |
| `AUTO_CREATE_TABLES` | `true` creates missing tables at boot. Set `false` once you run `database/migrations/` yourself. |

---

## 🧠 How the AI layer works

`AIService` is a boundary, not an SDK call site. `RuleBasedProvider` computes every insight from the user's own history and always works offline. Set `AI_PROVIDER=anthropic` with a key and the same three questions — daily reflection, weekly patterns, coach answer — are answered by a model, with an automatic fall back to the rule engine on any error or timeout. No screen knows which one replied.

The Coach is a conversation, not a search box. Every turn is stored in `conversations` / `chat_messages`, the last twelve turns are replayed to the provider, and the reply streams back as server-sent events — so "why?" is a real question and closing the tab does not lose the thread. The rule-based provider streams too (it chunks its finished answer), which is why no screen has to know which provider is talking. Both paths are charged against `AI_DAILY_LIMIT`, counted in the database so the cap holds across every gunicorn worker rather than per process.

---

## 📂 Structure

```text
consistency-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # HTTP layer only
│   │   ├── core/           # config, database, auth, error handling
│   │   ├── models/         # SQLAlchemy tables
│   │   ├── schemas/        # pydantic request/response contracts
│   │   ├── services/       # streaks, stats, AI, auth, goals
│   │   └── seed.py         # demo data
│   ├── tests/              # 32 tests
│   └── wsgi.py
├── frontend/src/
│   ├── api/                # typed client + shared types
│   ├── auth/               # AuthProvider / useAuth
│   ├── components/         # shell, chart, shared UI states
│   ├── hooks/              # useAsync
│   └── pages/              # one file per screen
├── database/migrations/    # SQL schema history
├── Dockerfile              # frontend build + backend runtime
├── docker-compose.yml      # app + MySQL
└── render.yaml             # one-click Render blueprint
```

---

## 📌 Author

**Anand Embadi** — [GitHub](https://github.com/EMBADIANAND) · [LinkedIn](https://www.linkedin.com/in/anand-embadi-7648082a3)

If this is useful to you, a ⭐ on the repo is appreciated.
