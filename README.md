# Pearls AQI Predictor

End-to-end AQI forecasting project using a serverless-friendly ML pipeline.

### Project Structure

```text
.
├── app/
├── config/
├── data/
│   └── raw/
├── feature_pipeline/
│   └── fetch_data.py
├── notebooks/
├── training_pipeline/
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your environment file:

```bash
cp .env.example .env
```

4. Add your AQICN token in `.env`.

Get a free token at https://aqicn.org/data-platform/token

## Fetch Raw AQI Data

Run:

```bash
python feature_pipeline/fetch_data.py
```

Optional city override:

```bash
python feature_pipeline/fetch_data.py --city Rawalpindi
```

The script stores the raw API response in:

`data/raw/sample.json`

It also prints a small summary of key weather and pollutant signals.