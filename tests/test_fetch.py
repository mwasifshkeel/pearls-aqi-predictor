import pandas as pd

from src.data import fetch_openmeteo


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_parse_hourly(monkeypatch):
    payload = {
        "hourly": {
            "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
            "temperature_2m": [20, 21],
        }
    }

    def dummy_get(url, params=None, timeout=60):
        return DummyResponse(payload)

    monkeypatch.setattr(fetch_openmeteo.requests, "get", dummy_get)

    df = fetch_openmeteo.fetch_forecast(33.6, 73.0)
    assert isinstance(df, pd.DataFrame)
    assert "timestamp" in df.columns


def test_fetch_air_quality_historical_params(monkeypatch):
    captured = {}

    def dummy_get(url, params=None, timeout=60):
        captured["url"] = url
        captured["params"] = params
        return DummyResponse({"hourly": {"time": []}})

    monkeypatch.setattr(fetch_openmeteo.requests, "get", dummy_get)

    fetch_openmeteo.fetch_air_quality(
        33.6,
        73.0,
        start_date="2024-05-01",
        end_date="2025-05-01",
    )

    assert captured["url"].endswith("/v1/air-quality")
    assert captured["params"]["start_date"] == "2024-05-01"
    assert captured["params"]["end_date"] == "2025-05-01"
    assert "past_days" not in captured["params"]
