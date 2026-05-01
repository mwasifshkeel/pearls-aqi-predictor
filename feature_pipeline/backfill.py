"""
Historical backfill: fetch 1 year of **daily** AQI summaries and save raw JSON + CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import date, timedelta
from pathlib import Path
from time import sleep
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.waqi.info/feed"


def get_station_id(city: str, token: str) -> int:
    """Fetch the station ID for a given city from the live feed."""
    url = f"{BASE_URL}/{city}/"
    resp = requests.get(url, params={"token": token}, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok" or not payload.get("data"):
        raise RuntimeError(f"Could not retrieve station for {city}: {payload}")
    station_id = payload["data"]["idx"]
    print(f"Found station ID {station_id} for city '{city}'")
    return station_id


def fetch_daily_summary(station_id: int, dt: date, token: str) -> Dict[str, Any]:
    """Fetch AQICN daily summary for a specific date."""
    url = f"{BASE_URL}/@{station_id}/"
    params = {"token": token, "date": dt.isoformat()}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(
            f"Fetch failed for {dt.isoformat()}: {data.get('data')}"
        )
    return data


def extract_daily_row(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a single daily row from a historical/daily response.
    The response iaqi dict contains single values like {"pm25": {"v": 154}, ...}.
    Returns a flat dict with the date and all measured parameters.
    """
    data = payload.get("data", {})
    if not data:
        return {}

    # Date from the response (time->s is 'YYYY-MM-DD HH:MM:SS')
    time_info = data.get("time", {})
    date_str = time_info.get("s", "")[:10]  # e.g. "2026-02-16"
    if not date_str:
        return {}

    row = {"date": date_str}

    # Extract iaqi values
    iaqi = data.get("iaqi", {})
    for key, obj in iaqi.items():
        # obj is a dict like {"v": 154}
        if isinstance(obj, dict) and "v" in obj:
            row[key] = obj["v"]

    # Optionally include the dominant pollutant and aqi
    row["dominentpol"] = data.get("dominentpol", "")
    row["aqi"] = data.get("aqi", None)  # top-level aqi is usually the computed one

    return row


def backfill(
    city: str,
    token: str,
    start_date: date,
    end_date: date,
    raw_dir: Path,
    csv_path: Path,
):
    """Main backfill loop – fetches daily summaries and writes CSV."""
    # 1. Get station ID
    station_id = get_station_id(city, token)

    # 2. Loop over dates
    csv_rows: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        date_str = current.isoformat()
        json_path = raw_dir / f"{date_str}.json"

        if json_path.exists():
            print(f"[{date_str}] Already fetched – loading from disk.")
            with open(json_path, "r") as f:
                payload = json.load(f)
        else:
            print(f"[{date_str}] Fetching...")
            try:
                payload = fetch_daily_summary(station_id, current, token)
            except Exception as e:
                print(f"  ERROR: {e} – skipping.")
                current += timedelta(days=1)
                continue

            # Save raw JSON
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w") as f:
                json.dump(payload, f, indent=2)

            sleep(0.5)  # rate‑limit

        # Extract row
        row = extract_daily_row(payload)
        if row:
            csv_rows.append(row)

        current += timedelta(days=1)

    # 3. Write combined CSV
    if csv_rows:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        # Dynamically get all fieldnames from all rows
        fieldnames = list(dict.fromkeys(k for row in csv_rows for k in row))
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nBackfill complete. {len(csv_rows)} days saved to {csv_path}")
    else:
        print("\nNo data extracted – check the JSON structure.")


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill 1 year of daily AQI data")
    parser.add_argument(
        "--city", default=None, help="City (default: AQICN_CITY from .env)"
    )
    parser.add_argument(
        "--start", default=None, help="Start date YYYY-MM-DD (default: 1 year ago)"
    )
    parser.add_argument(
        "--end", default=None, help="End date YYYY-MM-DD (default: today)"
    )
    return parser.parse_args()


def main():
    load_dotenv()

    city = os.getenv("AQICN_CITY", "Islamabad")
    token = os.getenv("AQICN_API_TOKEN", "").strip()
    if not token:
        raise EnvironmentError("AQICN_API_TOKEN is missing in .env")

    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today

    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw" / "historical"
    csv_path = project_root / "data" / "raw" / "historical_daily.csv"

    backfill(city, token, start_date, end_date, raw_dir, csv_path)


if __name__ == "__main__":
    main()