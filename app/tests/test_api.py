
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["catalog_size"] == 78


def test_movies_endpoint():
    response = client.get("/api/movies")

    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 78
    assert any(movie["title"] == "Interstellar" for movie in movies)


def test_recommendations_endpoint():
    response = client.get(
        "/api/recommendations",
        params={"liked": "1,2", "limit": 5},
    )

    assert response.status_code == 200
    recommendations = response.json()
    assert len(recommendations) <= 5
    assert all("title" in movie for movie in recommendations)


def test_metrics_endpoint():
    response = client.get("/api/metrics")

    assert response.status_code == 200
    data = response.json()
    assert data["catalog_size"] == 78
    assert "runtime" in data
