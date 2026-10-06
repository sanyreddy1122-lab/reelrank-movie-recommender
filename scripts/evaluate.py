"""Deterministic leave-one-out ranking check on bundled synthetic preferences."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommender import recommender

HISTORY = {
    "user_a": [1, 2, 4],
    "user_b": [5, 6, 8],
    "user_c": [9, 10, 12],
    "user_d": [13, 14, 16],
}

hits = 0
recommended = set()
cutoff = 5
for history in HISTORY.values():
    held_out, train = history[-1], history[:-1]
    recs = recommender.recommend(train, limit=cutoff)
    ids = {movie["id"] for movie in recs}
    hits += held_out in ids
    recommended.update(ids)
precision_at_k = hits / (len(HISTORY) * cutoff)
hit_rate_at_k = hits / len(HISTORY)
catalog_coverage_at_k = len(recommended) / len(recommender.movies)
print(f"users evaluated: {len(HISTORY)}")
print(f"precision@{cutoff}: {precision_at_k:.3f}")
print(f"hit rate@{cutoff}: {hit_rate_at_k:.3f}")
print(f"catalog coverage@{cutoff}: {catalog_coverage_at_k:.3f} ({len(recommended)}/{len(recommender.movies)})")
