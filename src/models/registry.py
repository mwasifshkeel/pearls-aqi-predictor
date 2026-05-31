from __future__ import annotations

import io
from typing import Dict, Any

from pymongo import MongoClient
import gridfs
from ..utils.mongo_client import get_database

import joblib

def push_model(model, name: str, metrics: Dict, artifacts_path: str) -> None:
    db = get_database()
    fs = gridfs.GridFS(db)
    
    # Serialize model to bytes
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)
    
    # Store in GridFS
    file_id = fs.put(buffer, filename=name, metadata={"metrics": metrics, "artifacts_path": artifacts_path})
    
    # Track latest version mapping
    db.model_registry.update_one(
        {"name": name},
        {"$set": {"name": name, "latest_file_id": file_id, "metrics": metrics}},
        upsert=True
    )

def get_model(name: str):
    db = get_database()
    fs = gridfs.GridFS(db)
    
    record = db.model_registry.find_one({"name": name})
    if not record:
        raise ValueError(f"Model {name} not found")
        
    grid_out = fs.get(record["latest_file_id"])
    model = joblib.load(io.BytesIO(grid_out.read()))
    return model
