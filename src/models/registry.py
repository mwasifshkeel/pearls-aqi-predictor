from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import mlflow
import mlflow.sklearn

import joblib
import requests

_DEFAULT_EXPERIMENT = "aqi_predictor"
_DEFAULT_STAGE = "Production"
_MODEL_FILENAME = "model.pkl"


def _normalize_env(value: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    if value is None:
        return fallback
    if str(value).strip() == "":
        return fallback
    return value


def _require_env(name: str, fallback: Optional[str] = None) -> str:
    value = _normalize_env(os.getenv(name), fallback)
    if not value:
        raise ValueError(f"{name} is required for the DagsHub model registry")
    return value


def _optional_env(name: str, fallback: Optional[str] = None) -> Optional[str]:
    return _normalize_env(os.getenv(name), fallback)


def _tracking_config() -> Dict[str, str]:
    tracking_uri = _optional_env("DAGSHUB_MLFLOW_URI", _optional_env("MLFLOW_TRACKING_URI"))
    if not tracking_uri:
        raise ValueError("DAGSHUB_MLFLOW_URI or MLFLOW_TRACKING_URI is required")
    username = _require_env("DAGSHUB_USERNAME", _optional_env("MLFLOW_TRACKING_USERNAME"))
    token = _require_env("DAGSHUB_TOKEN", _optional_env("MLFLOW_TRACKING_PASSWORD"))
    experiment_name = _optional_env("DAGSHUB_EXPERIMENT", _DEFAULT_EXPERIMENT)
    stage = _optional_env("DAGSHUB_MODEL_STAGE", _DEFAULT_STAGE)
    timeout = int(_optional_env("DAGSHUB_TIMEOUT_SECONDS", "30") or 30)
    return {
        "tracking_uri": tracking_uri.rstrip("/"),
        "username": username,
        "token": token,
        "experiment_name": experiment_name,
        "stage": stage,
        "timeout": str(timeout),
    }


def _session(config: Dict[str, str]) -> requests.Session:
    session = requests.Session()
    session.auth = (config["username"], config["token"])
    return session


def _post_json(session: requests.Session, base_url: str, path: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    response = session.post(f"{base_url}{path}", json=payload, timeout=timeout)
    if not response.ok:
        raise RuntimeError(f"DagsHub REST error {response.status_code} {path}: {response.text}")
    if response.text:
        return response.json()
    return {}


def _get_json(session: requests.Session, base_url: str, path: str, params: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    response = session.get(f"{base_url}{path}", params=params, timeout=timeout)
    if not response.ok:
        raise RuntimeError(f"DagsHub REST error {response.status_code} {path}: {response.text}")
    return response.json()


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_or_create_experiment(session: requests.Session, base_url: str, name: str, timeout: int) -> str:
    response = session.get(
        f"{base_url}/api/2.0/mlflow/experiments/get-by-name",
        params={"experiment_name": name},
        timeout=timeout,
    )
    if response.ok:
        payload = response.json()
        return str(payload["experiment"]["experiment_id"])
    if response.status_code != 404:
        raise RuntimeError(
            f"DagsHub REST error {response.status_code} get-by-name: {response.text}"
        )
    created = _post_json(
        session,
        base_url,
        "/api/2.0/mlflow/experiments/create",
        {"name": name},
        timeout,
    )
    return str(created["experiment_id"])



def _register_model(session: requests.Session, base_url: str, name: str, timeout: int) -> None:
    response = session.post(
        f"{base_url}/api/2.0/mlflow/registered-models/create",
        json={"name": name},
        timeout=timeout,
    )
    if response.ok:
        return
    if response.status_code == 400 and "RESOURCE_ALREADY_EXISTS" in response.text:
        return
    raise RuntimeError(
        f"DagsHub REST error {response.status_code} registered-models/create: {response.text}"
    )


def _create_model_version(
    session: requests.Session,
    base_url: str,
    name: str,
    run_id: str,
    source: str,
    timeout: int,
) -> str:
    payload = {"name": name, "run_id": run_id, "source": source}
    response = _post_json(session, base_url, "/api/2.0/mlflow/model-versions/create", payload, timeout)
    return str(response["model_version"]["version"])


def _transition_stage(
    session: requests.Session,
    base_url: str,
    name: str,
    version: str,
    stage: str,
    timeout: int,
) -> None:
    payload = {
        "name": name,
        "version": version,
        "stage": stage,
        "archive_existing_versions": True,
    }
    _post_json(session, base_url, "/api/2.0/mlflow/model-versions/transition-stage", payload, timeout)


def push_model(
    model,
    name: str,
    metrics: Dict[str, Any],
    artifacts_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    config = _tracking_config()
    timeout = int(config["timeout"])
    base_url = config["tracking_uri"]
    session = _session(config)

    # Configure MLflow to use DagsHub
    mlflow.set_tracking_uri(base_url)
    os.environ["MLFLOW_TRACKING_USERNAME"] = config["username"]
    os.environ["MLFLOW_TRACKING_PASSWORD"] = config["token"]

    experiment_id = _get_or_create_experiment(session, base_url, config["experiment_name"], timeout)
    tags = {
        "source": "training_pipeline",
        "model_name": name,
        "registry": "dagshub",
    }
    if metadata and metadata.get("model_type"):
        tags["model_type"] = str(metadata.get("model_type"))

    # Use MLflow SDK for the run — handles artifact storage correctly
    mlflow.set_experiment(config["experiment_name"])
    with mlflow.start_run(tags=tags) as run:
        run_id = run.info.run_id

        # Log metrics
        for key, value in metrics.items():
            coerced = _coerce_float(value)
            if coerced is not None:
                mlflow.log_metric(key, coerced)

        # Log params
        for key, value in (metadata or {}).items():
            if value is not None:
                mlflow.log_param(key, str(value))

        # Serialize model and log all artifacts from the artifacts dir
        artifact_root = Path(artifacts_path)
        artifact_root.mkdir(parents=True, exist_ok=True)
        model_path = artifact_root / _MODEL_FILENAME
        joblib.dump(model, model_path)
        mlflow.log_artifacts(str(artifact_root))  # uploads everything including model.pkl

        # Register model
        model_uri = f"runs:/{run_id}/{_MODEL_FILENAME}"
        _register_model(session, base_url, name, timeout)
        version = _create_model_version(session, base_url, name, run_id, model_uri, timeout)
        _transition_stage(session, base_url, name, version, config["stage"], timeout)

    return {
        "run_id": run_id,
        "version": version,
        "stage": config["stage"],
        "model_name": name,
    }


def get_model(name: str):
    config = _tracking_config()
    timeout = int(config["timeout"])
    base_url = config["tracking_uri"]
    session = _session(config)

    response = _post_json(
        session,
        base_url,
        "/api/2.0/mlflow/registered-models/get-latest-versions",
        {"name": name, "stages": [config["stage"]]},
        timeout,
    )
    versions = response.get("model_versions", [])
    if not versions:
        raise ValueError(f"Model {name} not found in DagsHub registry")

    model_version = versions[0]
    source = str(model_version.get("source", ""))

    if source.startswith("runs:/"):
        _, run_ref = source.split("runs:/", 1)
        run_id, artifact_path = run_ref.split("/", 1)
        download = session.get(
            f"{base_url}/api/2.0/mlflow/artifacts/download",
            params={"run_id": run_id, "path": artifact_path},
            timeout=timeout,
        )
        if not download.ok:
            raise RuntimeError(
                f"DagsHub REST error {download.status_code} artifacts/download: {download.text}"
            )
        return joblib.load(io.BytesIO(download.content))

    if not source:
        raise ValueError(f"Model {name} has no source artifact in DagsHub registry")

    download = session.get(source, timeout=timeout)
    if not download.ok:
        raise RuntimeError(
            f"DagsHub REST error {download.status_code} artifact fetch: {download.text}"
        )
    return joblib.load(io.BytesIO(download.content))
