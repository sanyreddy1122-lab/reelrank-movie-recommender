"""Deterministic leave-one-out ranking check on bundled synthetic preferences."""
import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.recommender import MODEL_VERSION, recommender
import mlflow

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

tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment("ReelRank-Recommender")
with mlflow.start_run(run_name="tfidf-content-evaluation"):
    mlflow.log_params({
        "model_version": MODEL_VERSION,
        "algorithm": "TF-IDF cosine similarity",
        "ngram_min": recommender.ngram_range[0],
        "ngram_max": recommender.ngram_range[1],
        "similarity_weight": recommender.similarity_weight,
        "rating_weight": recommender.rating_weight,
        "cutoff_k": cutoff,
        "evaluation_profiles": len(HISTORY),
        "catalog_size": len(recommender.movies),
    })
    mlflow.log_metrics({
        "precision_at_k": precision_at_k,
        "hit_rate_at_k": hit_rate_at_k,
        "catalog_coverage_at_k": catalog_coverage_at_k,
    })
    mlflow.set_tag("evaluation_type", "deterministic leave-one-out baseline")
    print(f"MLflow run: {mlflow.active_run().info.run_id}")
    print(f"MLflow tracking URI: {mlflow.get_tracking_uri()}")
