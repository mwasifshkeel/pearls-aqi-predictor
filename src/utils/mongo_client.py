import os
from pymongo import MongoClient

def get_mongo_client() -> MongoClient:
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise ValueError("MONGO_URI is required")
    return MongoClient(uri)

def get_database():
    client = get_mongo_client()
    db_name = os.getenv("MONGO_DB_NAME", "aqi_predictor")
    return client.get_database(db_name)
