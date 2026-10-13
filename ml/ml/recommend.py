
import json
from pathlib import Path

import pandas as pd
import torch
from torch import nn


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

MODEL_PATH = PROJECT_DIR / "models" / "matrix_factorization.pt"
MAPPINGS_PATH = PROJECT_DIR / "models" / "id_mappings.json"
RATINGS_PATH = PROJECT_DIR / "data" / "ml-100k" / "u.data"
MOVIES_PATH = PROJECT_DIR / "data" / "ml-100k" / "u.item"

USER_ID = 1
TOP_N = 10

print("ReelRank - PyTorch Movie Recommendation System")
print(f"Project folder: {PROJECT_DIR}")


# --------------------------------------------------
# 2. Define the same model architecture used in training
# --------------------------------------------------

class MatrixFactorization(nn.Module):
    def __init__(self, num_users, num_movies, embedding_dim):
        super().__init__()

        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.movie_embedding = nn.Embedding(num_movies, embedding_dim)

        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)

        self.global_bias = nn.Parameter(torch.tensor(3.5))

    def forward(self, users, movies):
        user_vectors = self.user_embedding(users)
        movie_vectors = self.movie_embedding(movies)

        interaction = (user_vectors * movie_vectors).sum(dim=1)

        return (
            interaction
            + self.user_bias(users).squeeze(1)
            + self.movie_bias(movies).squeeze(1)
            + self.global_bias
        )


# --------------------------------------------------
# 3. Check required files and load the model
# --------------------------------------------------

print("\nLoading ReelRank recommendation model...")

required_files = [
    MODEL_PATH,
    MAPPINGS_PATH,
    RATINGS_PATH,
    MOVIES_PATH,
]

for path in required_files:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

checkpoint = torch.load(
    MODEL_PATH,
    map_location="cpu",
    weights_only=True,
)

with MAPPINGS_PATH.open("r", encoding="utf-8") as file:
    mappings = json.load(file)

# Normalize mapping keys to strings for consistent lookup.
user_map = {
    str(key): int(value)
    for key, value in mappings["user_map"].items()
}

movie_map = {
    str(key): int(value)
    for key, value in mappings["movie_map"].items()
}

if str(USER_ID) not in user_map:
    raise ValueError(
        f"User {USER_ID} is missing from the trained model mappings."
    )

if len(movie_map) != checkpoint["num_movies"]:
    raise ValueError(
        "Movie mapping size does not match the model checkpoint. "
        "Check that the model and mappings were generated together."
    )

model = MatrixFactorization(
    num_users=checkpoint["num_users"],
    num_movies=checkpoint["num_movies"],
    embedding_dim=checkpoint["embedding_dim"],
)

model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

print("Model loaded successfully.")


# --------------------------------------------------
# 4. Load MovieLens ratings and movie titles
# --------------------------------------------------

ratings = pd.read_csv(
    RATINGS_PATH,
    sep="\t",
    names=["user_id", "movie_id", "rating", "timestamp"],
)

movies = pd.read_csv(
    MOVIES_PATH,
    sep="|",
    encoding="latin-1",
    header=None,
    usecols=[0, 1],
    names=["movie_id", "title"],
)

ratings["user_id"] = ratings["user_id"].astype(int)
ratings["movie_id"] = ratings["movie_id"].astype(int)
movies["movie_id"] = movies["movie_id"].astype(int)

# Find movies that user 1 has already rated.
seen_movies = set(
    ratings.loc[
        ratings["user_id"] == USER_ID,
        "movie_id",
    ].tolist()
)

# Exclude previously rated movies.
candidates = movies[
    ~movies["movie_id"].isin(seen_movies)
].copy()

# Movie IDs in JSON are strings, so convert IDs before mapping.
candidates["model_movie_idx"] = (
    candidates["movie_id"]
    .astype(str)
    .map(movie_map)
)

# Only use movies known to the trained model.
candidates = candidates.dropna(
    subset=["model_movie_idx"]
).copy()

candidates["model_movie_idx"] = (
    candidates["model_movie_idx"].astype(int)
)

if candidates.empty:
    raise ValueError(
        "No eligible movies found. Check that the movie IDs in "
        "u.item match the IDs in id_mappings.json."
    )

print(f"Movies already rated by user {USER_ID}: {len(seen_movies)}")
print(f"Eligible movies for recommendation: {len(candidates)}")


# --------------------------------------------------
# 5. Generate raw predictions
# --------------------------------------------------

user_idx = user_map[str(USER_ID)]

user_tensor = torch.full(
    (len(candidates),),
    user_idx,
    dtype=torch.long,
)

movie_tensor = torch.tensor(
    candidates["model_movie_idx"].to_numpy(),
    dtype=torch.long,
)

with torch.no_grad():
    raw_predictions = (
        model(user_tensor, movie_tensor)
        .cpu()
        .numpy()
    )

candidates["raw_prediction"] = raw_predictions

if not torch.isfinite(torch.tensor(raw_predictions)).all():
    raise ValueError(
        "The model produced invalid predictions. Check the trained weights."
    )

# Sort by raw predicted preference, not the rounded display rating.
recommendations = (
    candidates.sort_values(
        "raw_prediction",
        ascending=False,
    )
    .head(TOP_N)
    .copy()
)

# Ratings are bounded only for display.
recommendations["display_rating"] = (
    recommendations["raw_prediction"].clip(1.0, 5.0)
)


# --------------------------------------------------
# 6. Display prediction diagnostics and recommendations
# --------------------------------------------------

print("\nRaw prediction summary for eligible movies:")
print(f"Minimum: {raw_predictions.min():.3f}")
print(f"Maximum: {raw_predictions.max():.3f}")
print(f"Mean:    {raw_predictions.mean():.3f}")
print(
    "Predictions >= 5.0:",
    f"{(raw_predictions >= 5.0).sum()} / {len(raw_predictions)}",
)

print("\n" + "=" * 80)
print(f" TOP {TOP_N} MOVIE RECOMMENDATIONS FOR USER {USER_ID}")
print("=" * 80)

for rank, (_, movie) in enumerate(
    recommendations.iterrows(),
    start=1,
):
    print(
        f"{rank:2}. {movie['title']} "
        f"- Raw prediction: {movie['raw_prediction']:.3f} "
        f"| Estimated rating: {movie['display_rating']:.1f}/5"
    )

print("=" * 80)
print("\nRecommendation generation completed.")
