"""Small offline sanity metric on a deterministic synthetic preference split."""
from app.recommender import recommender

HISTORY = {
    "user_a": [1, 2, 4],
    "user_b": [5, 6, 8],
    "user_c": [9, 10, 12],
    "user_d": [13, 14, 16],
}

hits = covered = total = 0
for history in HISTORY.values():
    held_out, train = history[-1], history[:-1]
    recs = recommender.recommend(train, limit=5)
    ids = {movie["id"] for movie in recs}
    hits += held_out in ids
    covered += len(ids)
    total += 5
print(f"precision@5: {hits / (len(HISTORY) * 5):.3f}")
print(f"catalog coverage@5: {covered / len(recommender.movies):.3f}")
