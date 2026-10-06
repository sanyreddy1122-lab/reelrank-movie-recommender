import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import storage
from app.recommender import recommender


ROOT = Path(__file__).resolve().parents[1]
SESSION_COOKIE = "reelrank_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14
SESSION_SECRET = storage.session_secret()
app = FastAPI(title="ReelRank Movie Recommender", version="0.2.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
storage.initialize()


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)
    legacy_user_id: str | None = Field(default=None, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)


class Feedback(BaseModel):
    movie_id: int
    user_id: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    action: str = Field(pattern=r"^(like|dislike|watchlist|unlike|unwatchlist)$")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _make_session(user_id: str) -> str:
    payload = _b64url(json.dumps({"sub": user_id, "exp": int(time.time()) + SESSION_TTL_SECONDS}, separators=(",", ":")).encode())
    signature = hmac.new(SESSION_SECRET, payload.encode("ascii"), hashlib.sha256).digest()
    return f"{payload}.{_b64url(signature)}"


def _session_user(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    try:
        payload, supplied_signature = token.split(".", 1)
        expected_signature = _b64url(hmac.new(SESSION_SECRET, payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return None
        padded = payload + "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if int(claims["exp"]) < int(time.time()):
            return None
        return storage.get_user_by_id(claims["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def require_user(request: Request) -> dict:
    user = _session_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def _set_session_cookie(response: Response, request: Request, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _make_session(user_id),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


def _check_user_scope(path_user_id: str, user: dict) -> None:
    if path_user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only access your own movie profile.")


@app.get("/", include_in_schema=False)
def home(request: Request):
    if _session_user(request):
        return FileResponse(ROOT / "static" / "index.html")
    return FileResponse(ROOT / "static" / "login.html")


@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if _session_user(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(ROOT / "static" / "login.html")


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest, request: Request, response: Response):
    user = storage.create_user(payload.display_name, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    if payload.legacy_user_id:
        storage.transfer_feedback(payload.legacy_user_id, user["id"])
    _set_session_cookie(response, request, user["id"])
    return {"user": user}


@app.post("/api/auth/login")
def authenticate(payload: LoginRequest, request: Request, response: Response):
    user = storage.authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    _set_session_cookie(response, request, user["id"])
    return {"user": user}


@app.get("/api/auth/me")
def current_account(user: dict = Depends(require_user)):
    return user


@app.post("/api/auth/logout", status_code=200)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return {"logged_out": True}


@app.get("/health")
def health():
    return {"status": "ok", "model": "tfidf-content-v1", "catalog_size": len(recommender.movies)}


@app.get("/api/movies")
def movies(search: str = "", genre: str = "", language: str = ""):
    result = recommender.movies
    if search:
        q = search.casefold()
        result = [m for m in result if q in m["title"].casefold() or q in m.get("original_title", "").casefold() or q in m["overview"].casefold()]
    if genre:
        result = [m for m in result if genre in m["genres"]]
    if language:
        result = [m for m in result if m.get("language") == language]
    return result


def _recommend(liked: str, limit: int, genre: str, user_id: str | None = None, language: str = ""):
    try:
        ids = [int(item) for item in liked.split(",") if item]
    except ValueError as exc:
        raise HTTPException(400, "liked must be comma-separated movie IDs") from exc
    excluded = []
    if user_id:
        pref = storage.preferences(user_id)
        ids = list(dict.fromkeys(ids + pref["liked"]))
        excluded = list(dict.fromkeys(pref["disliked"] + pref["watchlist"]))
    return recommender.recommend(ids, limit, genre or None, excluded, language or None)


@app.get("/api/recommendations")
def recommendations(request: Request, liked: str = "", limit: int = Query(8, ge=1, le=20), genre: str = "", language: str = "", user_id: str | None = None):
    if user_id:
        user = require_user(request)
        _check_user_scope(user_id, user)
    return _recommend(liked, limit, genre, user_id, language)


@app.get("/api/users/{user_id}/recommendations")
def user_recommendations(user_id: str, limit: int = Query(10, ge=1, le=20), genre: str = "", language: str = "", user: dict = Depends(require_user)):
    _check_user_scope(user_id, user)
    return _recommend("", limit, genre, user_id, language)


@app.get("/api/users/{user_id}/preferences")
def user_preferences(user_id: str, user: dict = Depends(require_user)):
    _check_user_scope(user_id, user)
    return storage.preferences(user_id)


@app.get("/api/users/{user_id}/watchlist")
def user_watchlist(user_id: str, user: dict = Depends(require_user)):
    _check_user_scope(user_id, user)
    ids = storage.preferences(user_id)["watchlist"]
    return [recommender.by_id[mid] for mid in ids if mid in recommender.by_id]


@app.post("/api/feedback", status_code=202)
def feedback(payload: Feedback, user: dict = Depends(require_user)):
    if payload.user_id and payload.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only update your own movie profile.")
    if payload.movie_id not in recommender.by_id:
        raise HTTPException(404, "Movie not found")
    storage.record_feedback(user["id"], payload.movie_id, payload.action)
    return {"accepted": True, "user_id": user["id"]}


@app.get("/api/metrics")
def metrics():
    return {"model": "tfidf-content-v1", "catalog_size": len(recommender.movies), **storage.feedback_summary()}
