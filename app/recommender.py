import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "movies.json"
MODEL_VERSION = "tfidf-content-v1"


class Recommender:
    def __init__(self, path: Path = DATA_PATH):
        self.ngram_range = (1, 2)
        self.similarity_weight = 0.85
        self.rating_weight = 0.15
        self.movies = json.loads(path.read_text(encoding="utf-8"))
        for movie in self.movies:
            movie.setdefault("language", "en")
            movie.setdefault("language_name", "English")
            movie.setdefault("original_title", movie["title"])
        self.by_id = {movie["id"]: movie for movie in self.movies}
        text = [" ".join([*m["genres"], *m["keywords"], m["overview"], m["language_name"]]) for m in self.movies]
        self.matrix = TfidfVectorizer(stop_words="english", ngram_range=self.ngram_range, min_df=1).fit_transform(text)

    def recommend(self, liked_ids: list[int], limit: int = 8, genre: str | None = None,
                  exclude_ids: list[int] | None = None, language: str | None = None) -> list[dict]:
        liked = [mid for mid in liked_ids if mid in self.by_id]
        excluded = set(exclude_ids or [])
        if liked:
            indices = [next(i for i, m in enumerate(self.movies) if m["id"] == mid) for mid in liked]
            profile = np.asarray(self.matrix[indices].mean(axis=0))
            scores = cosine_similarity(profile, self.matrix).ravel()
        else:
            scores = [0.0] * len(self.movies)
        ranked = []
        for i, movie in enumerate(self.movies):
            if (movie["id"] in liked or movie["id"] in excluded
                    or (genre and genre not in movie["genres"])
                    or (language and movie.get("language") != language)):
                continue
            # A small rating prior breaks near-ties without overwhelming taste similarity.
            score = float(scores[i]) * self.similarity_weight + (movie["rating"] / 10) * self.rating_weight
            ranked.append((score, movie))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        ranked = ranked[:limit]
        best_score = ranked[0][0] if ranked else 0
        return [
            {**movie, "match": round(score / best_score * 100) if best_score else 0}
            for score, movie in ranked
        ]


recommender = Recommender()
