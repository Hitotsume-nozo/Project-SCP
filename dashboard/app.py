# analytics/query_service.py
import json
import sys
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from minio import Minio
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)

app = FastAPI(
    title="Smart City Analytics API",
    description="Real-time urban traffic and pollution analytics with automated data governance",
    version="2.0.0",
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


def load_records(bucket, prefix, limit=500):
    client = get_minio()
    records = []
    try:
        objects = list(client.list_objects(bucket, prefix=prefix, recursive=True))
        # Get most recent files only
        objects.sort(key=lambda x: x.object_name, reverse=True)
        objects = objects[:limit]

        for obj in objects:
            response = client.get_object(bucket, obj.object_name)
            data = json.loads(response.read().decode())
            records.append(data)
            response.close()
    except Exception as e:
        print(f"Error loading {bucket}/{prefix}: {e}", flush=True)
    return records


def count_objects(bucket, prefix):
    client = get_minio()
    try:
        objects = list(client.list_objects(bucket, prefix=prefix, recursive=True))
        return len(objects)
    except:
        return 0


# ========== HEALTH ==========
@app.get("/")
def root():
    return {
        "service": "Smart City Analytics API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ========== GOVERNANCE ==========
@app.get("/api/v1/governance/stats")
def governance_stats():
    traffic_curated = load_records("curated-zone", "traffic/", limit=1000)
    pollution_curated = load_records("curated-zone", "pollution/", limit=1000)

    # Count raw zone files too
    raw_count = count_objects("raw-zone", "traffic/")

    pii_count = sum(1 for r in traffic_curated if r.get("pii_detected"))
    clean_count = sum(1 for r in traffic_curated if not r.get("pii_detected"))
    alert_count = sum(
        1 for r in pollution_curated if r.get("alert_level") in ["CRITICAL", "WARNING"]
    )
    critical_count = sum(
        1 for r in pollution_curated if r.get("alert_level") == "CRITICAL"
    )

    total_traffic = len(traffic_curated)
    compliance_rate = (
        round((pii_count / total_traffic) * 100, 1) if total_traffic > 0 else 0
    )

    return {
        "traffic_records_processed": total_traffic,
        "traffic_records_with_pii": pii_count,
        "traffic_records_clean": clean_count,
        "pii_detection_rate": compliance_rate,
        "pii_governance_rate": 100.0 if pii_count > 0 else 0,
        "raw_zone_files": raw_count,
        "pollution_records_processed": len(pollution_curated),
        "pollution_alerts_warning": alert_count - critical_count,
        "pollution_alerts_critical": critical_count,
        "pollution_alerts_total": alert_count,
        "last_updated": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/governance/comparison")
def governance_comparison():
    raw = load_records("raw-zone", "traffic/", limit=5)
    governed = load_records("curated-zone", "traffic/", limit=5)

    if raw and governed:
        return {
            "raw_sample": raw[0],
            "governed_sample": governed[0],
            "explanation": (
                "The license_plates field in raw data contains actual plate "
                "numbers. In governed data, each plate is replaced with a "
                "truncated SHA-256 hash, preserving analytical utility "
                "(unique counting) while eliminating re-identification risk."
            ),
        }
    return {"message": "No data available yet"}


@app.get("/api/v1/governance/timeline")
def governance_timeline():
    """Returns governance activity over time for charting"""
    records = load_records("curated-zone", "traffic/", limit=200)

    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)

    if "governed_at" not in df.columns:
        return {"message": "No governance timestamps found"}

    df["governed_at"] = pd.to_datetime(df["governed_at"])
    df["minute"] = df["governed_at"].dt.floor("min")

    timeline = (
        df.groupby("minute")
        .agg(
            records_processed=("pii_detected", "count"),
            pii_found=("pii_detected", "sum"),
        )
        .reset_index()
    )

    timeline["minute"] = timeline["minute"].astype(str)
    timeline = timeline.sort_values("minute")

    return timeline.to_dict(orient="records")


# ========== TRAFFIC ==========
@app.get("/api/v1/traffic/summary")
def traffic_summary():
    records = load_records("curated-zone", "traffic/", limit=500)
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)

    summary = (
        df.groupby("district")
        .agg(
            total_records=("vehicle_count", "count"),
            avg_vehicles=("vehicle_count", "mean"),
            max_vehicles=("vehicle_count", "max"),
            min_vehicles=("vehicle_count", "min"),
            avg_speed=("avg_speed_kmh", "mean"),
            min_speed=("avg_speed_kmh", "min"),
            max_speed=("avg_speed_kmh", "max"),
        )
        .reset_index()
    )

    summary = summary.round(1)
    return summary.to_dict(orient="records")


@app.get("/api/v1/traffic/latest")
def traffic_latest(limit: int = Query(default=25, le=100)):
    records = load_records("curated-zone", "traffic/", limit=limit)
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records[:limit]


@app.get("/api/v1/traffic/timeseries")
def traffic_timeseries():
    """Traffic volume over time by district"""
    records = load_records("curated-zone", "traffic/", limit=300)
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["minute"] = df["timestamp"].dt.floor("min")

    ts = (
        df.groupby(["minute", "district"])
        .agg(
            avg_vehicles=("vehicle_count", "mean"), avg_speed=("avg_speed_kmh", "mean")
        )
        .reset_index()
    )

    ts["minute"] = ts["minute"].astype(str)
    ts = ts.round(1)
    return ts.to_dict(orient="records")


# ========== POLLUTION ==========
@app.get("/api/v1/pollution/summary")
def pollution_summary():
    records = load_records("curated-zone", "pollution/", limit=500)
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)

    summary = (
        df.groupby("district")
        .agg(
            avg_aqi=("aqi", "mean"),
            max_aqi=("aqi", "max"),
            min_aqi=("aqi", "min"),
            avg_pm25=("pm25", "mean"),
            max_pm25=("pm25", "max"),
            avg_co2=("co2_ppm", "mean"),
            readings=("aqi", "count"),
        )
        .reset_index()
    )

    summary = summary.round(1)
    return summary.to_dict(orient="records")


@app.get("/api/v1/pollution/alerts")
def pollution_alerts(limit: int = Query(default=30, le=100)):
    records = load_records("curated-zone", "pollution/", limit=200)
    alerts = [r for r in records if r.get("alert_level") in ["CRITICAL", "WARNING"]]
    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    critical = [a for a in alerts if a.get("alert_level") == "CRITICAL"]
    warning = [a for a in alerts if a.get("alert_level") == "WARNING"]

    return {
        "total_alerts": len(alerts),
        "critical_count": len(critical),
        "warning_count": len(warning),
        "alerts": alerts[:limit],
    }


@app.get("/api/v1/pollution/latest")
def pollution_latest(limit: int = Query(default=25, le=100)):
    records = load_records("curated-zone", "pollution/", limit=limit)
    records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return records[:limit]


@app.get("/api/v1/pollution/timeseries")
def pollution_timeseries():
    """AQI over time by district"""
    records = load_records("curated-zone", "pollution/", limit=300)
    if not records:
        return {"message": "No data yet"}

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["minute"] = df["timestamp"].dt.floor("min")

    ts = (
        df.groupby(["minute", "district"])
        .agg(avg_aqi=("aqi", "mean"), avg_pm25=("pm25", "mean"))
        .reset_index()
    )

    ts["minute"] = ts["minute"].astype(str)
    ts = ts.round(1)
    return ts.to_dict(orient="records")
