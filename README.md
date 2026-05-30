# AQI Predictor — Rawalpindi (Open-Meteo + MongoDB)

End-to-end serverless AQI forecasting pipeline using Open-Meteo for data, Hopsworks for feature store/model registry, GitHub Actions for orchestration, and a Next.js dashboard.

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

## Repo Structure

See [AQI_Project_Plan.md](AQI_Project_Plan.md) for the full implementation plan and dataset details.
