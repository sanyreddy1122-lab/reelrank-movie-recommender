# ReelRank — MLOps-Based Movie Recommendation System

ReelRank is a movie recommendation project that combines a web-based recommendation service with machine learning experiments and MLOps tools.

## Features

- Movie recommendations based on movie content and user preferences
- FastAPI backend for serving recommendations
- Movie catalog with 78 movies
- User feedback and account-related functionality
- PyTorch matrix factorization experiment using MovieLens 100K
- MLflow experiment tracking
- Saved model weights and movie/user ID mappings
- Automated API tests using Pytest

## Architecture

### 1. Website recommendation service

The current website uses a TF-IDF content-based recommendation model to serve recommendations through FastAPI.

### 2. PyTorch recommendation experiment

A separate experiment trains a matrix factorization model using the MovieLens 100K dataset. The trained model and ID mappings are saved under `models/`.

**Important:** The PyTorch experiment is currently separate from the website's TF-IDF recommendation service. The two systems should not be treated as one integrated production model.

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Website recommendation model | TF-IDF content-based filtering |
| ML experiment | PyTorch matrix factorization |
| Experiment tracking | MLflow |
| Dataset for ML experiment | MovieLens 100K |
| Testing | Pytest |
| Version control | Git and GitHub |
| Deployment | Render |

## Project Structure

```text
reelrank-movie-recommender/
├── app/
│   ├── main.py
│   ├── recommender.py
│   ├── storage.py
│   └── tests/
│       └── test_api.py
├── ml/
│   ├── train_model.py
│   └── ml/
│       └── recommend.py
├── models/
│   ├── id_mappings.json
│   └── matrix_factorization.pt
├── data/
├── static/
├── scripts/
├── .github/
│   └── workflows/
├── Dockerfile
└── .gitignore
```

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/sanyreddy1122-lab/reelrank-movie-recommender.git
cd reelrank-movie-recommender
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the dependencies listed in the project's existing requirements file. If the project does not contain one, set up a requirements file before running this step.

### 4. Start the API

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the API health endpoint:

`http://127.0.0.1:8000/health`

Interactive API documentation:

`http://127.0.0.1:8000/docs`

## Run Automated Tests

With the virtual environment activated and project dependencies installed:

```powershell
python -m pytest -v
```

The API test suite covers the health endpoint, movie catalog, recommendations, and metrics.

## Train the PyTorch Experiment

The PyTorch experiment uses the MovieLens 100K dataset. Download and extract the dataset according to the training script's requirements, then run:

```powershell
python ml/train_model.py
```

The experiment saves the trained model and ID mappings in the `models/` directory and logs training information to MLflow.

Run the experiment's recommendation script using the Python environment and arguments expected by `ml/ml/recommend.py`.

## MLOps Learning Goals

- Track experiments and training metrics with MLflow.
- Version source code and model artifacts with Git.
- Validate API behavior using automated tests.
- Explore model performance and recommendation quality.
- Develop a safe process for connecting the trained PyTorch model to the website after creating a reliable mapping between the datasets.

## Future Improvements

- Integrate the PyTorch model with the serving API using a verified movie-ID mapping.
- Automate tests and checks through GitHub Actions.
- Add model and data quality monitoring.
- Establish a reproducible model retraining workflow.
- Track recommendation quality as user interactions change.

## Project Status

The FastAPI website recommender and the separate PyTorch/MLflow experiment are available as distinct components. Full integration of the PyTorch model into the website is future work.

## Author

Developed as a learning project focused on recommendation systems, machine learning, and MLOps.
