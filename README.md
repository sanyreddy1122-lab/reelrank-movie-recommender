# ReelRank — MLOps Movie Recommender

A small, runnable movie recommendation product built as an MLOps starter. It includes a FastAPI service, a content-based recommendation baseline, a responsive web interface, Docker Compose, and a path to evolve the model and data pipeline.

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

If `py --version` is not recognized, Python is not installed or its launcher is unavailable; install Python first. If you use PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead. Open http://localhost:8000. The app starts with a bundled sample catalog; no API keys or external data downloads are needed.

## Run with Docker

```sh
docker compose up --build
```

## MLOps lifecycle

- `data/movies.json` is the versioned demo catalog.
- `app/recommender.py` builds TF-IDF vectors from genres, keywords, and summaries and ranks by cosine similarity plus a modest quality prior.
- `app/main.py` exposes health, catalog, user preference, recommendation, feedback, and aggregate metric endpoints. Feedback is persisted in SQLite at `data/feedback.sqlite3`; latest likes shape each user's profile, dislikes are excluded, and watchlist events are retained.
- The browser calls the FastAPI service on the same origin. Favorites, dismissals, recommendation refreshes, movie details, and the saved Watchlist are backed by the API; watchlist actions are persisted and saved movies are excluded from recommendations.
- `scripts/evaluate.py` reports precision@k and catalog coverage on a deterministic leave-one-out split from the sample interactions.
- Docker Compose runs the API as a container. Replace the bundled catalog with a versioned ingestion job, store model artifacts in a model registry, and add CI/CD and monitoring as the next production steps.
- `PROJECT_REPORT.md` maps the design, research references, evaluation results, and implementation evidence to the course review rubric.

This is an educational baseline, not a production-trained model. The sample catalog and interactions are synthetic, and the content model has no personal data.

## Backend API

FastAPI's interactive endpoint guide is available at http://localhost:8000/docs while the app is running.

- `GET /health` — service and model status.
- `GET /api/movies?search=&genre=` — searchable movie catalog.
- `GET /api/users/{user_id}/preferences` — saved likes, dislikes, and watchlist.
- `GET /api/users/{user_id}/watchlist` — saved movie records for the Watchlist UI.
- `GET /api/users/{user_id}/recommendations?limit=10` — personalized recommendations.
- `POST /api/feedback` — persist `{ "user_id": "demo", "movie_id": 1, "action": "like" }`; actions are `like`, `dislike`, `unlike`, `watchlist`, and `unwatchlist`.
- `GET /api/metrics` — aggregate feedback counts without returning user-level data.

After changing Python backend code, restart Uvicorn so the process loads the new routes and database schema. For development, run `py -m uvicorn app.main:app --reload` from the project directory.

The demo browser creates a random local user ID. SQLite is suitable for local development; deploy with managed storage and authentication before serving multiple users publicly.
