# AQI Predictor — Rawalpindi (Open-Meteo + MongoDB)

End-to-end serverless AQI forecasting pipeline using Open-Meteo for data, MongoDB for the feature store, DagsHub MLflow (REST) for the model registry, GitHub Actions for orchestration, and a Next.js dashboard. Predictions are written to MongoDB and snapshot as DagsHub artifacts each training run.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set environment variables:

```bash
export MONGO_URI=your_mongodb_uri
export MONGO_DB_NAME=aqi_predictor
export DAGSHUB_MLFLOW_URI=https://dagshub.com/<owner>/<repo>.mlflow
export DAGSHUB_USERNAME=your_dagshub_username
export DAGSHUB_TOKEN=your_dagshub_token
export DAGSHUB_EXPERIMENT=aqi_predictor
export DAGSHUB_MODEL_STAGE=Production
```

Run pipelines locally:

```bash
python pipelines/feature_pipeline.py
python pipelines/training_pipeline.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `MONGO_URI` (and optionally `MONGO_DB_NAME`) in your environment or Vercel dashboard for API routes.

## GitHub Actions

Set repository secrets:

- `MONGO_URI`
- `MONGO_DB_NAME` (optional)
- `RAWALPINDI_LAT`, `RAWALPINDI_LON` (optional overrides)
- `TRAINING_WINDOW_DAYS` (default is 90)
- `DAGSHUB_MLFLOW_URI`
- `DAGSHUB_USERNAME`
- `DAGSHUB_TOKEN`
- `DAGSHUB_EXPERIMENT` (optional, defaults to `aqi_predictor`)
- `DAGSHUB_MODEL_STAGE` (optional, defaults to `Production`)