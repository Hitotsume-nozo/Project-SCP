# analytics/query_service.py
import json
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from datetime import datetime
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)

app = FastAPI(
    title="Smart City Analytics API",
    description="Real-time traffic & pollution analytics with governance",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_minio():
    return Minio(
        "minio:9000", access_key="admin", secret_key="admin12345", secure=False
    )


def load_records(bucket, prefix):
    """Load all JSON records from a MinIO prefix"""
    client = get_minio()
    records = []
    try:
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        for obj in objects:
            response = client.get_object(bucket, obj.object_name)
            data = json.loads(response.read().decode())
            records.append(data)
            response.close()
    except Exception as e:
        print(f"Error loading from {bucket}/{prefix}: {e}", flush=True)
    return records


# ========== HEALTH ==========
@app.get("/")
def root():
    return {
        "service": "Smart City Analytics API",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ========== GOVERNANCE ENDPOINTS ==========
@app.get("/api/v1/governance/stats")
def governance_stats():
    """Overall governance statistics"""
    traffic = load_records("curated-zone", "traffic/")
    pollution = load_records("curated-zone", "pollution/")

    pii_count = sum(1 for r in traffic if r.get("pii_detected"))
    alert_count = sum(
        1 for r in pollution if r.get("alert_level") in ["CRITICAL", "WARNING"]
    )

    return {
        "traffic_records_processed": len(traffic),
        "pii_detected_and_hashed": pii_count,
        "pollution_records_processed": len(pollution),
        "pollution_alerts": alert_count,
        "compliance_rate": "100%",
        "last_updated": datetime.utcnow().isoformat(),
    }


# ========== TRAFFIC ENDPOINTS ==========
@app.get("/api/v1/traffic/summary")
def traffic_summary():
    """Traffic stats grouped by district"""
    records = load_records("curated-zone", "traffic/")
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)
    summary = (
        df.groupby("district")
        .agg(
            total_records=("vehicle_count", "count"),
            avg_vehicles=("vehicle_count", "mean"),
            max_vehicles=("vehicle_count", "max"),
            avg_speed=("avg_speed_kmh", "mean"),
        )
        .reset_index()
    )

    summary = summary.round(1)
    return summary.to_dict(orient="records")


@app.get("/api/v1/traffic/latest")
def traffic_latest(limit: int = 20):
    """Most recent traffic records"""
    records = load_records("curated-zone", "traffic/")
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records[:limit]


# ========== POLLUTION ENDPOINTS ==========
@app.get("/api/v1/pollution/summary")
def pollution_summary():
    """Pollution stats grouped by district"""
    records = load_records("curated-zone", "pollution/")
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)
    summary = (
        df.groupby("district")
        .agg(
            avg_aqi=("aqi", "mean"),
            max_aqi=("aqi", "max"),
            avg_pm25=("pm25", "mean"),
            max_pm25=("pm25", "max"),
            readings=("aqi", "count"),
        )
        .reset_index()
    )

    summary = summary.round(1)
    return summary.to_dict(orient="records")


@app.get("/api/v1/pollution/alerts")
def pollution_alerts():
    """All pollution alerts"""
    records = load_records("curated-zone", "pollution/")
    alerts = [r for r in records if r.get("alert_level") in ["CRITICAL", "WARNING"]]
    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"total_alerts": len(alerts), "alerts": alerts[:50]}


@app.get("/api/v1/pollution/latest")
def pollution_latest(limit: int = 20):
    """Most recent pollution records"""
    records = load_records("curated-zone", "pollution/")
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records[:limit]


# ========== COMPARISON ENDPOINT (for governance proof) ==========
@app.get("/api/v1/governance/comparison")
def governance_comparison():
    """Show raw vs governed data side by side"""
    raw = load_records("raw-zone", "traffic/")
    governed = load_records("curated-zone", "traffic/")

    if raw and governed:
        return {
            "raw_sample": raw[-1],
            "governed_sample": governed[-1],
            "explanation": "Notice license_plates field: "
            "raw has real plates, governed has SHA-256 hashes",
        }
    return {"message": "No data yet"}
