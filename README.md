# ReelRank — MLOps Movie Recommender

A small, runnable movie recommendation product built as an MLOps starter. It includes a FastAPI service, a content-based recommendation baseline, a cinematic streaming-style responsive interface, a multilingual catalog, movie poster artwork, Docker Compose, and a path to evolve the model and data pipeline.

**Live Render demo:** [reelrank-movie-recommender.onrender.com](https://reelrank-movie-recommender.onrender.com)

## Run locally on Windows

First install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/). In the installer, enable **Add python.exe to PATH**. Close and reopen Command Prompt after installation.

In Command Prompt, run:

```bat
cd /d C:\Users\sanyr\OneDrive\Documents\ChatGPT\mlops
py --version
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

If `py --version` is not recognized, Python is not installed or its launcher is unavailable; install Python first. If you use PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead. Open http://localhost:8000. The app starts with a bundled sample catalog; no API keys or external data downloads are needed. Movie poster thumbnails are looked up from English Wikipedia when the page loads; the built-in artwork remains as a fallback when a poster is unavailable.

## Run with Docker

```sh
docker compose up --build
```

## Render deployment

The live demo is configured by the root-level `render.yaml` Blueprint. It runs FastAPI with Render's Python runtime, installs `requirements.txt`, binds Uvicorn to Render's `$PORT`, checks `/health`, and waits for GitHub Actions before automatically deploying new `main` commits. To recreate it in another Render workspace, use the [one-click Render setup](https://render.com/deploy?repo=https://github.com/sanyreddy1122-lab/reelrank-movie-recommender), connect GitHub, and deploy the Blueprint.

The intentionally shared demo login is `demo@example.com` with password `ReelRankDemo2026!`. The app refreshes this demo account on startup so the credentials work after a restart. Anyone can use this account and change its shared likes and watchlist; do not store private information in it.

This Blueprint selects Render's free web-service plan. Free services can sleep when idle, and their files are temporary; demo accounts, likes, and watchlists can be cleared after a restart or deploy. Use a paid persistent disk or move account and feedback storage to a managed database for durable public use. Blueprint changes may require a sync in the Render dashboard.

## MLOps lifecycle

- `data/movies.json` is the versioned demo catalog.
- `app/recommender.py` builds TF-IDF vectors from genres, keywords, and summaries and ranks by cosine similarity plus a modest quality prior.
- `app/main.py` exposes health, catalog, user preference, recommendation, feedback, and aggregate metric endpoints. Feedback is persisted in SQLite at `data/feedback.sqlite3`; latest likes shape each user's profile, dislikes are excluded, and watchlist events are retained.
- Account registration and login use PBKDF2 password hashes and signed HttpOnly session cookies. The server creates a local signing key in `data/session.key` (ignored by Git); set `REELRANK_SECRET_KEY` to a shared secret when deploying multiple app instances.
- Personalized preference, recommendation, Watchlist, and feedback routes require a valid session and only allow access to the signed-in account's profile. Catalog and health routes remain public.
- The browser calls the FastAPI service on the same origin. Favorites, dismissals, recommendation refreshes, movie details, and the saved Watchlist are backed by the API; watchlist actions are persisted and saved movies are excluded from recommendations.
- The Explore shelf browses 78 demo titles across 27 original languages, with search across English and original-language titles, language and genre filters, and top-rated, newest, title, or shortest sorting.
- Movie cards and detail views load poster thumbnails from Wikipedia's PageImages API and link to their source article. ReelRank does not own the poster images.
- `scripts/evaluate.py` reports precision@k and catalog coverage on a deterministic leave-one-out split from the sample interactions.
- Docker Compose runs the API as a container. Replace the bundled catalog with a versioned ingestion job, store model artifacts in a model registry, and add CI/CD and monitoring as the next production steps.
- `PROJECT_REPORT.md` maps the design, research references, evaluation results, and implementation evidence to the course review rubric.

This is an educational baseline, not a production-trained model. The movie catalog and evaluation histories are sample data. Account passwords are stored as salted PBKDF2 hashes; account details and movie preferences are stored locally in SQLite. Use a managed identity provider, HTTPS, and managed persistent storage before deploying for public users.

## Backend API

FastAPI's interactive endpoint guide is available at http://localhost:8000/docs while the app is running.

- `GET /health` — service and model status.
- `POST /api/auth/register` — create an account with `display_name`, `email`, and a password of at least 10 characters; the response sets the signed session cookie.
- `POST /api/auth/login` — verify email/password and set the session cookie.
- `GET /api/auth/me` and `POST /api/auth/logout` — inspect the current account or end its session.
- `GET /api/movies?search=&genre=&language=` — searchable catalog with original-language filtering.
- `GET /api/users/{user_id}/preferences` — signed-in account's saved likes, dislikes, and watchlist; the ID must match the current session.
- `GET /api/users/{user_id}/watchlist` — saved movie records for the Watchlist UI.
- `GET /api/users/{user_id}/recommendations?limit=10&language=ko` — personalized recommendations, optionally limited to an original language.
- `POST /api/feedback` — authenticated feedback payload `{ "movie_id": 1, "action": "like" }`; actions are `like`, `dislike`, `unlike`, `watchlist`, and `unwatchlist`.
- `GET /api/metrics` — aggregate feedback counts without returning user-level data.

After changing Python backend code, restart Uvicorn so the process loads the new routes and database schema. For development, run `py -m uvicorn app.main:app --reload` from the project directory.

The browser redirects signed-out visitors to the login page. SQLite is suitable for local development; use a managed identity provider and database before serving public users at scale.
