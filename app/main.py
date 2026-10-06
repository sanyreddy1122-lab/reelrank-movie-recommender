from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.recommender import recommender
from app import storage


ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="ReelRank Movie Recommender", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
storage.initialize()


class Feedback(BaseModel):
    movie_id: int
    user_id: str = Field(default="demo", min_length=1, max_length=80, pattern="^[a-zA-Z0-9_-]+$")
    action: str = Field(pattern="^(like|dislike|watchlist|unlike|unwatchlist)$")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "model": "tfidf-content-v1", "catalog_size": len(recommender.movies)}


@app.get("/api/movies")
def movies(search: str = "", genre: str = ""):
    result = recommender.movies
    if search:
        q = search.casefold()
        result = [m for m in result if q in m["title"].casefold() or q in m["overview"].casefold()]
    if genre:
        result = [m for m in result if genre in m["genres"]]
    return result


def _recommend(liked: str, limit: int, genre: str, user_id: str | None = None):
    try:
        ids = [int(item) for item in liked.split(",") if item]
    except ValueError as exc:
        raise HTTPException(400, "liked must be comma-separated movie IDs") from exc
    excluded = []
    if user_id:
        pref = storage.preferences(user_id)
        ids = list(dict.fromkeys(ids + pref["liked"]))
        excluded = list(dict.fromkeys(pref["disliked"] + pref["watchlist"]))
    return recommender.recommend(ids, limit, genre or None, excluded)


@app.get("/api/recommendations")
def recommendations(liked: str = "", limit: int = Query(8, ge=1, le=20), genre: str = "", user_id: str | None = None):
    return _recommend(liked, limit, genre, user_id)


@app.get("/api/users/{user_id}/recommendations")
def user_recommendations(user_id: str, limit: int = Query(10, ge=1, le=20), genre: str = ""):
    return _recommend("", limit, genre, user_id)


@app.get("/api/users/{user_id}/preferences")
def user_preferences(user_id: str):
    return storage.preferences(user_id)


@app.get("/api/users/{user_id}/watchlist")
def user_watchlist(user_id: str):
    ids = storage.preferences(user_id)["watchlist"]
    return [recommender.by_id[mid] for mid in ids if mid in recommender.by_id]


@app.post("/api/feedback", status_code=202)
def feedback(payload: Feedback):
    if payload.movie_id not in recommender.by_id:
        raise HTTPException(404, "Movie not found")
    storage.record_feedback(payload.user_id, payload.movie_id, payload.action)
    return {"accepted": True, "user_id": payload.user_id}


@app.get("/api/metrics")
def metrics():
    return {"model": "tfidf-content-v1", "catalog_size": len(recommender.movies), **storage.feedback_summary()}
