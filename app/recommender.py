import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "movies.json"


class Recommender:
    def __init__(self, path: Path = DATA_PATH):
        self.movies = json.loads(path.read_text(encoding="utf-8"))
        self.by_id = {movie["id"]: movie for movie in self.movies}
        text = [" ".join([*m["genres"], *m["keywords"], m["overview"]]) for m in self.movies]
        self.matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1).fit_transform(text)

    def recommend(self, liked_ids: list[int], limit: int = 8, genre: str | None = None,
                  exclude_ids: list[int] | None = None) -> list[dict]:
        liked = [mid for mid in liked_ids if mid in self.by_id]
        excluded = set(exclude_ids or [])
        if liked:
            indices = [next(i for i, m in enumerate(self.movies) if m["id"] == mid) for mid in liked]
            profile = self.matrix[indices].mean(axis=0)
            scores = cosine_similarity(profile, self.matrix).ravel()
        else:
            scores = [0.0] * len(self.movies)
        ranked = []
        for i, movie in enumerate(self.movies):
            if movie["id"] in liked or movie["id"] in excluded or (genre and genre not in movie["genres"]):
                continue
            # A small rating prior breaks near-ties without overwhelming taste similarity.
            score = float(scores[i]) * 0.85 + (movie["rating"] / 10) * 0.15
            ranked.append((score, movie))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [{**movie, "match": round(score * 100)} for score, movie in ranked[:limit]]


recommender = Recommender()
