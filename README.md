# AQI Forecasting System - Rawalpindi

Comprehensive technical report and developer README for the Pearls AQI Forecasting System, a reproducible end-to-end ML pipeline that ingests hourly Open‑Meteo data, constructs engineered features, trains multi‑output AQI forecast models, registers artefacts in DagsHub MLflow, and serves forecasts via a Next.js dashboard. This document is written for developers, data scientists, and operators who will run, extend, or audit the system.

Authors: Muhammad Wasif Shakeel
Target city: Rawalpindi (33.6007°N, 73.0679°E)



Project Overview
----------------

This repository implements a production‑oriented AQI forecasting system that:

- Collects hourly weather and air‑quality data from Open‑Meteo.
- Builds a rich feature catalog including temporal encodings, lag features (1h → 168h), rolling statistics, pollutant indices, and domain‑derived signals.
- Stores processed features in MongoDB (`aqi_features_rawalpindi`) as a feature store.
- Trains multi‑output models predicting 72 hours ahead using the latest 90‑day training window by default.
- Benchmarks candidate models (LightGBM, XGBoost, CatBoost, RandomForest, ExtraTrees, GRU/LSTM) and registers the best model to DagsHub MLflow.
- Writes forecasts (with confidence heuristics) to MongoDB (`aqi_predictions_rawalpindi`) and serves them to a Next.js 14 dashboard.

Goals
- Produce accurate and explainable 72‑hour AQI forecasts.
- Make experimentation reproducible: data, features, metrics, and model artefacts are versioned and snapshotted.
- Keep the system light on infra: GitHub Actions schedule pipelines, MongoDB acts as a lightweight feature store, and the frontend is serverless‑friendly.


Live Demo
---------
The dashboard is publicly accessible at: [Deployed Website](https://pearls-aqi-predictor.vercel.app/)


Quickstart (Local Development)
------------------------------

Prerequisites
- Python 3.10+
- Node 18+ (for the frontend)
- MongoDB instance accessible from your machine (Atlas or local)
- Optional: DagsHub credentials for MLflow remote registry

Setup (local Python env)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Env vars (example)

```bash
export MONGO_URI='mongodb+srv://<user>:<pass>@cluster0.mongodb.net'
export MONGO_DB_NAME='aqi_predictor'
# Optional for DagsHub/MLflow
export DAGSHUB_MLFLOW_URI='https://dagshub.com/<owner>/<repo>.mlflow'
export DAGSHUB_USERNAME='<username>'
export DAGSHUB_TOKEN='<token>'
```

Run pipelines

```bash
# Create initial feature store backfill
python pipelines/backfill_pipeline.py --days 365

# Run incremental feature pipeline (idempotent)
python pipelines/feature_pipeline.py

# Run training benchmark (writes best model files to debug_exports/)
python pipelines/training_pipeline.py
```

Frontend

```bash
cd frontend
npm install
npm run dev
# open http://localhost:3000
```

Architecture and Pipeline
-------------------------

High level flow:

1. Ingestion: `pipelines/feature_pipeline.py` queries Open‑Meteo (historical + forecast) and converts raw payloads to hourly rows.
2. Feature Engineering: `src/features/*` computes lag features, rolling statistics, temporal encodings, pollutant indices, and small spatial/time aggregates.
3. Feature Store: processed rows are upserted to MongoDB (`aqi_features_rawalpindi`) with deduplication and idempotent batching.
4. Training: `pipelines/training_pipeline.py` loads the latest window (configurable: default 90 days), constructs supervised matrices for multi‑output training (72 steps), trains candidate models, collects metrics, computes SHAP explanations (tree models), and registers the best model to DagsHub MLflow.
5. Prediction: `src/models/*` include predictors that serialize forecasts to MongoDB (`aqi_predictions_rawalpindi`) used by the Next.js API routes under `frontend/app/api`.

Pipeline design considerations
- Idempotency: ingestion and feature upserts are safe to re-run.
- Leakage prevention: training matrices are constructed with a guard that excludes any rows whose future horizon would overlap the current UTC hour.
- Monitoring: training runs log metrics to MLflow + store summary CSVs in `debug_exports/` for quick inspection.

Data Sources and Feature Engineering
-----------------------------------

Open‑Meteo provides hourly weather and air‑quality model variables used as raw inputs. Key steps in the feature pipeline:

- Timestamp normalisation to UTC and strict hourly alignment.
- Forward‑fill missing short gaps, then zero‑fill remaining NaNs before training matrix construction.
- Generate lag features per pollutant and AQI at horizons 1h, 2h, 3h, 6h, 12h, 24h, 48h, 72h, 168h.
- Rolling windows (3h, 6h, 12h, 24h, 48h, 168h) produce mean/min/std features used to capture accumulation and dispersion patterns.
- Domain features include `pressure_change_6h`, `precipitation_cumulative_72h`, `days_since_last_rain`, `oxidant_index`, and traffic proxies (`hour_traffic_weight`, `is_evening_rush`, `weekend_traffic_factor`).

Feature Catalog
- The canonical `TOP_FEATURES` set (40 features) is derived from permutation importance on a held‑out validation window. It balances model performance and operational availability in the live collection.

Exploratory Data Analysis - Key Findings
--------------------------------------

Dataset
- Several thousand hourly records covering multiple years depending on ingestion history.
- Hourly coverage typically 97–99% with a small number of isolated gaps; the largest single gap is a few hours.

AQI distribution
- Right‑skewed with occasional spikes above 80–100.
- The bulk of hours sit in AQI 20–60 range; spikes dominate RMSE.

Temporal patterns
- Winter months (Nov–Jan) show higher mean AQI due to inversions and burning events.
- Monsoon months have lower AQI.

Feature correlations
- `european_aqi_lag_1h` is the strongest single predictor (|r| ~ 0.92).
- Rolling AQI statistics (3h, 24h) and PM‑based rolling means are strongly correlated with target.

Missingness and live compatibility
- Long‑horizon lags (168h) have non‑zero null rates at the beginning of the series but approach zero later.
- Top features are present in the live prediction collection with comparable null rates, ensuring operational parity.

Modelling Approach
------------------

Forecast formulation
- Multi‑output regression predicting 72 hourly averages ahead from a single snapshot (shape: (n_samples, 72)).
- This balances computational cost (single model) with the need to model temporal decay across horizons.

Model candidates and configuration
- LightGBM: tuned with 200–300 estimators, learning_rate 0.03–0.05, num_leaves 15.
- XGBoost: tree_method hist, 300 estimators, learning_rate 0.05.
- CatBoost: 400 iterations, learning_rate 0.05, depth 6.
- RandomForest / ExtraTrees: 400 trees, max_depth 20 as sensible defaults.
- GradientBoostingRegressor (scikit): 300 estimators.
- GRU / LSTM: baseline architectures included but not prioritised for daily benchmarking due to longer training times.

Training details
- Default training window is 90 days; split ratio 90/10 train/val to ensure leakage‑free evaluation.
- Evaluation metrics: RMSE, MAE, R² overall + per‑horizon metrics aggregated to day1/day2/day3 averages (24h windows).
- SHAP explanations computed for tree models; permutation importance used to derive `TOP_FEATURES`.

Evaluation & Benchmarks - Summary
--------------------------------

Representative numbers (subject to dataset snapshot):
- Best tree models: test RMSE ≈ 11–12 AQI units; test R² ≈ 0.40–0.45 on 72‑hour forecast.
- Naive baselines: persistence (t+1=t) RMSE is low for 1‑hour horizon but seasonal naives (24h, 168h) are worse; the ML models outperform seasonal naive baselines at matching horizons.

The Overfitting Challenge - Detailed Account
-------------------------------------------

Observed symptoms
- Training R² routinely reaches 0.88–0.95 across tree families inside the 90‑day window.
- Test R² on held‑out 72‑hour horizon stalls around ~0.44 despite many attempts at regularisation and feature selection.
- RMSE test ≈ 11–12 AQI units, indicating decent central tendency capture but poor precision at spikes.

What we tried and observations

- Feature reduction: removed long lags, redundant rolling windows, and low‑importance features. Training R² decreased but test R² did not improve.
- Lag ablation: removing AQI lag features severely degraded test performance - lag features are genuinely informative and cannot be discarded.
- Stronger model regularisation: lower learning rates, shallower trees, stronger L1/L2 penalties - training fit dropped but test R² ceiling persisted.
- Window sweeping: 7, 30, 60, 90, 180, 365 days tested - 90 days is empirically best. Longer windows introduce seasonal heterogeneity that reduces test performance.

Conclusion from experiments
- The persistent train/test gap is likely caused by an information deficit - the available inputs (Open‑Meteo modelled AQI + weather) do not capture the generative processes behind local pollution spikes (traffic variation, local emissions, agricultural/biomass burning events). Model capacity and regularisation alone cannot fix this.

Operational Details
-------------------

Storage
- MongoDB holds feature rows (`aqi_features_rawalpindi`), live predictions (`aqi_features_live_rawalpindi`), and output forecasts (`aqi_predictions_rawalpindi`).

CI / Orchestration
- GitHub Actions schedule daily ingestion and training workflows. Training pushes artifacts to DagsHub MLflow via REST.

Explainability and Diagnostics
- SHAP summary plots for tree models are computed and stored as JSON artefacts.
- `debug_exports/` contains CSVs and JSONs for model benchmarks, top features, and selected metadata to support reproducibility.

Reproduction Checklist
---------------------

1. Configure `MONGO_URI` and `MONGO_DB_NAME`.
2. Run a backfill to populate the feature store:

```bash
python pipelines/backfill_pipeline.py --days 365
```

3. Run the incremental feature pipeline:

```bash
python pipelines/feature_pipeline.py
```

4. Run training benchmark and register the best model:

```bash
python pipelines/training_pipeline.py
```

5. Launch the frontend (optional):

```bash
cd frontend
npm install
npm run dev
```

Key Files and Where to Look
--------------------------

- `pipelines/feature_pipeline.py` - ingestion and feature upsert logic.
- `src/features/*` - feature engineering modules (lag, rolling, time, pollutant indices).
- `pipelines/training_pipeline.py` - training loop, model benchmarking, MLflow registration.
- `src/models/train.py` - model training helper that supports tree and DL models.
- `src/models/shap_explain.py` - SHAP integration.
- `debug_exports/` - output artefacts from runs (best_model_name.txt, feature_importance.csv, model_benchmark_metrics.csv).
- `frontend/` - Next.js dashboard and API routes that read MongoDB collections.


run SHAP on a sample and use `kmeans` background summarisation to speed up tree SHAP.

Contact
-------
- [Muhammad Wasif Shakeel](mailto:mwasifshkeel@gmail.com)