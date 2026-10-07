"""Compare the current movie catalog with the checked-in reference snapshot."""
import argparse
import json
import os
from pathlib import Path

import pandas as pd
import mlflow
from evidently import Report
from evidently.presets import DataDriftPreset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "data" / "reference" / "movies_baseline.csv"
DEFAULT_CURRENT = ROOT / "data" / "movies.json"
DEFAULT_OUTPUT = ROOT / "reports" / "data-drift-report.html"


def catalog_features(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        movies = json.loads(path.read_text(encoding="utf-8"))
        rows = [{
            "year": movie.get("year"),
            "rating": movie.get("rating"),
            "runtime": movie.get("runtime"),
            "language": movie.get("language", "en"),
            "genre_count": len(movie.get("genres", [])),
            "keyword_count": len(movie.get("keywords", [])),
        } for movie in movies]
        return pd.DataFrame(rows)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.reference.exists():
        parser.error(f"reference data file not found: {args.reference}")
    if not args.current.exists():
        parser.error(f"current data file not found: {args.current}")

    reference = catalog_features(args.reference)
    current = catalog_features(args.current)
    snapshot = Report([DataDriftPreset()]).run(
        reference_data=reference,
        current_data=current,
        name="reelrank-catalog-drift",
        metadata={"model": "tfidf-content-v1", "reference": args.reference.name},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    snapshot.save_html(str(args.output))
    print(f"Reference rows: {len(reference)}")
    print(f"Current rows:   {len(current)}")
    print(f"Data drift report: {args.output}")

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("ReelRank-Recommender")
    with mlflow.start_run(run_name="evidently-catalog-drift-report"):
        mlflow.log_params({
            "model_version": "tfidf-content-v1",
            "reference_rows": len(reference),
            "current_rows": len(current),
            "feature_count": len(current.columns),
        })
        mlflow.set_tag("evaluation_type", "Evidently catalog data drift")
        mlflow.log_artifact(str(args.output), artifact_path="data-drift")
        print(f"MLflow run: {mlflow.active_run().info.run_id}")


if __name__ == "__main__":
    main()
