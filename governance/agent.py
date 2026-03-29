# governance/agent.py
import json
import hashlib
import time
import sys
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from minio import Minio
from io import BytesIO
import threading

sys.stdout.reconfigure(line_buffering=True)

# === CONFIG ===
REDPANDA = "redpanda:9092"
PII_FIELDS = ["license_plates"]

# === SHARED STATS ===
stats = {
    "traffic_processed": 0,
    "pii_hashed": 0,
    "pollution_processed": 0,
    "alerts_triggered": 0,
}


def hash_pii(value):
    if isinstance(value, list):
        return [hashlib.sha256(v.encode()).hexdigest()[:12] for v in value]
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def govern_traffic(record):
    clean = record.copy()
    pii_found = False
    for field in PII_FIELDS:
        if field in clean and clean[field]:
            clean[field] = hash_pii(clean[field])
            pii_found = True
    clean["pii_detected"] = pii_found
    clean["governed_at"] = datetime.utcnow().isoformat()
    return clean, pii_found


def govern_pollution(record):
    """Add alert flags for dangerous readings"""
    clean = record.copy()
    aqi = clean.get("aqi", 0)

    if aqi > 300:
        clean["alert_level"] = "CRITICAL"
        clean["alert_message"] = f"DANGEROUS AQI ({aqi}) in {clean.get('district')}"
    elif aqi > 150:
        clean["alert_level"] = "WARNING"
        clean["alert_message"] = f"High AQI ({aqi}) in {clean.get('district')}"
    else:
        clean["alert_level"] = "NORMAL"
        clean["alert_message"] = None

    clean["governed_at"] = datetime.utcnow().isoformat()
    return clean


def connect_minio():
    print("Connecting to MinIO...", flush=True)
    client = Minio(
        "minio:9000", access_key="admin", secret_key="admin12345", secure=False
    )
    for bucket in ["raw-zone", "curated-zone"]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Created bucket: {bucket}", flush=True)
    return client


def save_json(minio_client, bucket, record, prefix):
    data = json.dumps(record, indent=2).encode()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    path = f"{prefix}/{ts}.json"
    minio_client.put_object(
        bucket, path, BytesIO(data), len(data), content_type="application/json"
    )


def make_producer():
    while True:
        try:
            p = KafkaProducer(
                bootstrap_servers=REDPANDA,
                value_serializer=lambda v: json.dumps(v).encode(),
            )
            return p
        except:
            time.sleep(3)


def make_consumer(topic, group):
    while True:
        try:
            c = KafkaConsumer(
                topic,
                bootstrap_servers=REDPANDA,
                value_deserializer=lambda m: json.loads(m.decode()),
                auto_offset_reset="earliest",
                group_id=group,
            )
            return c
        except:
            time.sleep(3)


# ========== TRAFFIC GOVERNANCE THREAD ==========
def traffic_governance():
    consumer = make_consumer("city.traffic.raw", "gov-traffic-v3")
    producer = make_producer()
    minio_client = connect_minio()

    print("[TRAFFIC] Governance thread started", flush=True)

    for msg in consumer:
        raw = msg.value
        governed, had_pii = govern_traffic(raw)

        save_json(minio_client, "raw-zone", raw, "traffic")
        save_json(minio_client, "curated-zone", governed, "traffic")
        producer.send("city.traffic.governed", value=governed)

        stats["traffic_processed"] += 1
        if had_pii:
            stats["pii_hashed"] += 1

        print(
            f"[TRAFFIC #{stats['traffic_processed']}] "
            f"PII_Hashed: {stats['pii_hashed']} | "
            f"District: {raw.get('district')}",
            flush=True,
        )


# ========== POLLUTION GOVERNANCE THREAD ==========
def pollution_governance():
    consumer = make_consumer("city.pollution.raw", "gov-pollution-v3")
    producer = make_producer()
    minio_client = connect_minio()

    print("[POLLUTION] Governance thread started", flush=True)

    for msg in consumer:
        raw = msg.value
        governed = govern_pollution(raw)

        save_json(minio_client, "curated-zone", governed, "pollution")
        producer.send("city.pollution.governed", value=governed)

        stats["pollution_processed"] += 1
        if governed.get("alert_level") in ["CRITICAL", "WARNING"]:
            stats["alerts_triggered"] += 1

        alert = governed.get("alert_level", "NORMAL")
        print(
            f"[POLLUTION #{stats['pollution_processed']}] "
            f"AQI: {raw.get('aqi')} | "
            f"Alert: {alert} | "
            f"District: {raw.get('district')}",
            flush=True,
        )


# ========== STATS PRINTER THREAD ==========
def print_stats():
    while True:
        time.sleep(30)
        print(f"\n{'=' * 50}", flush=True)
        print(f"GOVERNANCE STATS @ {datetime.utcnow().isoformat()}", flush=True)
        print(f"  Traffic Processed: {stats['traffic_processed']}", flush=True)
        print(f"  PII Hashed:        {stats['pii_hashed']}", flush=True)
        print(f"  Pollution Processed: {stats['pollution_processed']}", flush=True)
        print(f"  Alerts Triggered:  {stats['alerts_triggered']}", flush=True)
        print(f"{'=' * 50}\n", flush=True)


# ========== MAIN ==========
def main():
    print("=" * 50, flush=True)
    print("GOVERNANCE AGENT v2.0", flush=True)
    print("Processing: Traffic (PII) + Pollution (Alerts)", flush=True)
    print("=" * 50, flush=True)

    t1 = threading.Thread(target=traffic_governance, daemon=True)
    t2 = threading.Thread(target=pollution_governance, daemon=True)
    t3 = threading.Thread(target=print_stats, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
