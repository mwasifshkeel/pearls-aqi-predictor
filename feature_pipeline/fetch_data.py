"""Fetch raw AQI and weather data from AQICN and save JSON locally."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.waqi.info/feed"


def fetch_aqicn_feed(city: str, token: str) -> dict:
    """Call AQICN feed endpoint for a city and return the raw JSON response."""
    encoded_city = quote(city.strip())
    url = f"{BASE_URL}/{encoded_city}/"
    response = requests.get(url, params={"token": token}, timeout=30)
    response.raise_for_status()

    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(
            f"AQICN returned non-ok status: {payload.get('status')} - {payload.get('data')}"
        )

    return payload


def save_raw_payload(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch AQICN city data")
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City to query (defaults to AQICN_CITY from .env)",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    args = parse_args()
    city = args.city or os.getenv("AQICN_CITY", "Islamabad")
    token = os.getenv("AQICN_API_TOKEN", "").strip()

    if not token:
        raise EnvironmentError(
            "AQICN_API_TOKEN is missing. Add it to your .env file."
        )

    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "raw" / "sample.json"

    payload = fetch_aqicn_feed(city=city, token=token)
    save_raw_payload(payload, output_path)

    print("Saved raw AQICN payload to:", output_path)
    print("Payload:")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
