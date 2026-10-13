
import json
import os
import random
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

SEED = 42
EMBEDDING_DIM = 32
EPOCHS = 10
BATCH_SIZE = 1024
LEARNING_RATE = 0.005
WEIGHT_DECAY = 1e-5

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "ml-100k" / "u.data"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "matrix_factorization.pt"
MAPPINGS_PATH = MODEL_DIR / "id_mappings.json"

DEVICE = torch.device("cpu")


# --------------------------------------------------
# 2. Load MovieLens ratings
# --------------------------------------------------

if not DATA_FILE.exists():
    raise FileNotFoundError(
        f"Ratings file not found: {DATA_FILE}\n"
        "Check that data/ml-100k/u.data exists."
    )

ratings = pd.read_csv(
    DATA_FILE,
    sep="\t",
    names=["user_id", "movie_id", "rating", "timestamp"],
)

if ratings.empty:
    raise ValueError("The ratings dataset is empty.")

ratings = ratings.dropna(
    subset=["user_id", "movie_id", "rating"]
).copy()

# Convert IDs to native Python integers.
ratings["user_id"] = ratings["user_id"].astype(int)
ratings["movie_id"] = ratings["movie_id"].astype(int)
ratings["rating"] = ratings["rating"].astype(float)

# Create zero-based indexes for embedding layers.
user_ids = sorted(int(x) for x in ratings["user_id"].unique())
movie_ids = sorted(int(x) for x in ratings["movie_id"].unique())

user_map = {user_id: idx for idx, user_id in enumerate(user_ids)}
movie_map = {movie_id: idx for idx, movie_id in enumerate(movie_ids)}

ratings["user_idx"] = ratings["user_id"].map(user_map).astype(int)
ratings["movie_idx"] = ratings["movie_id"].map(movie_map).astype(int)

print(f"Ratings loaded: {len(ratings):,}")
print(f"Unique users: {len(user_ids):,}")
print(f"Unique movies: {len(movie_ids):,}")


# --------------------------------------------------
# 3. Split into training and test datasets
# --------------------------------------------------

ratings = ratings.sample(
    frac=1,
    random_state=SEED,
).reset_index(drop=True)

split_index = int(len(ratings) * 0.8)

train_df = ratings.iloc[:split_index].copy()
test_df = ratings.iloc[split_index:].copy()

if train_df.empty or test_df.empty:
    raise ValueError("Training or test dataset is empty.")

print(f"Training ratings: {len(train_df):,}")
print(f"Test ratings: {len(test_df):,}")


# --------------------------------------------------
# 4. Define the PyTorch model
# --------------------------------------------------

class MatrixFactorization(nn.Module):
    def __init__(self, num_users, num_movies, embedding_dim=32):
        super().__init__()

        self.user_embedding = nn.Embedding(
            num_users, embedding_dim
        )
        self.movie_embedding = nn.Embedding(
            num_movies, embedding_dim
        )

        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)

        self.global_bias = nn.Parameter(torch.tensor(3.5))

        nn.init.normal_(self.user_embedding.weight, std=0.05)
        nn.init.normal_(self.movie_embedding.weight, std=0.05)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)

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


model = MatrixFactorization(
    num_users=len(user_ids),
    num_movies=len(movie_ids),
    embedding_dim=EMBEDDING_DIM,
).to(DEVICE)


# --------------------------------------------------
# 5. Prepare the training loader
# --------------------------------------------------

train_dataset = TensorDataset(
    torch.tensor(
        train_df["user_idx"].to_numpy(),
        dtype=torch.long,
    ),
    torch.tensor(
        train_df["movie_idx"].to_numpy(),
        dtype=torch.long,
    ),
    torch.tensor(
        train_df["rating"].to_numpy(),
        dtype=torch.float32,
    ),
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
)

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
)

loss_fn = nn.MSELoss()


# --------------------------------------------------
# 6. Configure MLflow
# --------------------------------------------------

tracking_uri = os.environ.get(
    "MLFLOW_TRACKING_URI",
    f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}",
)

mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment("ReelRank-Recommender")


# --------------------------------------------------
# 7. Train, evaluate, and log the model
# --------------------------------------------------

with mlflow.start_run(
    run_name="pytorch-matrix-factorization"
):
    mlflow.log_params({
        "algorithm": "PyTorch matrix factorization",
        "embedding_dim": EMBEDDING_DIM,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "num_users": len(user_ids),
        "num_movies": len(movie_ids),
        "seed": SEED,
        "device": str(DEVICE),
        "split_ratio": "80/20",
    })

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0

        for users, movies, targets in train_loader:
            users = users.to(DEVICE)
            movies = movies.to(DEVICE)
            targets = targets.to(DEVICE)

            optimizer.zero_grad()

            predictions = model(users, movies)
            loss = loss_fn(predictions, targets)

            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(targets)

        average_loss = total_loss / len(train_dataset)

        mlflow.log_metric(
            "training_mse",
            average_loss,
            step=epoch + 1,
        )

        print(
            f"Epoch {epoch + 1}/{EPOCHS} "
            f"- training MSE: {average_loss:.4f}"
        )

    # Evaluate on the held-out test ratings.
    model.eval()

    with torch.no_grad():
        test_users = torch.tensor(
            test_df["user_idx"].to_numpy(),
            dtype=torch.long,
        )
        test_movies = torch.tensor(
            test_df["movie_idx"].to_numpy(),
            dtype=torch.long,
        )
        actual = test_df["rating"].to_numpy(dtype=np.float32)

        predicted = model(
            test_users,
            test_movies,
        ).cpu().numpy()

    rmse = float(np.sqrt(np.mean((predicted - actual) ** 2)))
    mae = float(np.mean(np.abs(predicted - actual)))

    print(f"\nTest RMSE: {rmse:.4f}")
    print(f"Test MAE:  {mae:.4f}")

    mlflow.log_metrics({
        "test_rmse": rmse,
        "test_mae": mae,
    })

    mlflow.set_tag(
        "evaluation_type",
        "random 80/20 rating split",
    )

    # Save the trained model and its ID mappings.
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "num_users": len(user_ids),
        "num_movies": len(movie_ids),
        "embedding_dim": EMBEDDING_DIM,
        "user_map": user_map,
        "movie_map": movie_map,
        "user_ids": user_ids,
        "movie_ids": movie_ids,
    }

    torch.save(checkpoint, MODEL_PATH)

    # Use string keys and native integers for valid JSON.
    mappings = {
        "user_map": {
            str(key): int(value)
            for key, value in user_map.items()
        },
        "movie_map": {
            str(key): int(value)
            for key, value in movie_map.items()
        },
        "user_ids": [int(x) for x in user_ids],
        "movie_ids": [int(x) for x in movie_ids],
    }

    with MAPPINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(mappings, file, indent=2)

    # Log the model and mappings as MLflow artifacts.
    mlflow.log_artifact(
        str(MODEL_PATH),
        artifact_path="model",
    )

    mlflow.log_artifact(
        str(MAPPINGS_PATH),
        artifact_path="model",
    )

    print(f"\nSaved model: {MODEL_PATH}")
    print(f"Saved mappings: {MAPPINGS_PATH}")
    print(f"MLflow run ID: {mlflow.active_run().info.run_id}")
    print(f"MLflow tracking URI: {mlflow.get_tracking_uri()}")

print("\nTraining and MLflow logging completed successfully.")
