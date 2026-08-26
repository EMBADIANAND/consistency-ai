# Deploying ConsistencyAI

Everything in the repo is ready. What is left needs your GitHub and Render accounts, so it has to run from your machine. Budget about ten minutes.

---

## 1. Move the CI workflow into place

The file bridge cannot write into `.github/workflows/`, so the workflow was delivered at the repo root. In PowerShell, from the `consistency-ai` folder:

```powershell
New-Item -ItemType Directory -Force -Path .github\workflows
Move-Item -Force ci.github-workflow.yml .github\workflows\ci.yml
```

---

## 2. Check it locally (optional, 2 minutes)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q          # expect 70 passed
python -m app.main           # http://127.0.0.1:5000
```

In a second terminal:

```powershell
cd frontend
npm install
npm test                     # expect 21 passed
npm run dev                  # http://localhost:5173
```

Want data to look at? With the backend venv active:

```powershell
$env:FLASK_APP="app"; flask seed
```

That creates `demo@consistency.ai` / `demo-password-123` with 45 days of history.

---

## 3. Push to GitHub

Your `.env` is already in `.gitignore`, so your secrets stay local. From the `consistency-ai` folder:

```powershell
git add -A
git commit -m "Wire frontend to API, add streaming coach conversation, containerise for deploy"
git push origin main
```

If the remote is not set yet:

```powershell
git remote add origin https://github.com/EMBADIANAND/consistency-ai.git
git branch -M main
git push -u origin main
```

---

## 4. Create the Render service

1. Go to <https://dashboard.render.com> and sign in with GitHub.
2. **New → Blueprint**, pick the `consistency-ai` repo. Render reads `render.yaml` on its own.
3. Click **Apply**.

That single step provisions a PostgreSQL database, generates `SECRET_KEY` and `JWT_SECRET_KEY`, injects `DATABASE_URL`, builds the Dockerfile and health-checks `/api/v1/health`. The first build takes roughly five minutes because it compiles the frontend inside the image.

Your app lands at `https://consistency-ai.onrender.com` (Render will show the exact URL).

### Two things to know about the free plan

- A free web service **spins down after 15 minutes without traffic**, and the next visitor waits about a minute for it to wake. Fine for a portfolio link; not fine for real daily use.
- A **free Postgres database expires 30 days after creation**, with a 14-day grace period to upgrade before it is deleted. Set a reminder — otherwise your data goes with it. Upgrading the database to the cheapest paid tier removes both problems.

Sources: [Render free tier docs](https://render.com/docs/free)

---

## 5. Turn on the real model (optional)

Out of the box the coach answers from a deterministic rule engine — no key, no cost, works offline. To have Claude answer instead, in the Render dashboard under your service's **Environment**:

| Key | Value |
| --- | --- |
| `AI_PROVIDER` | `anthropic` |
| `ANTHROPIC_API_KEY` | your key from <https://console.anthropic.com> |

Save and Render redeploys. If the key is wrong or the API is down, every call falls back to the rule engine automatically — users see an answer either way, and `ai_provider` in the response tells you which one replied.

`AI_DAILY_LIMIT` (default 100) caps AI-answered requests per account per day. Leave it on; it is the only thing stopping one account from looping a request and spending your whole API budget.

---

## Afterwards

- Visit `https://<your-url>/api/v1/health` — it should report `"database": "ok"`.
- Register an account through the UI and plan a day, so the app is not empty when you share the link.
- CI now runs the backend tests, the frontend tests and a Docker build on every push.
