# governance/agent.py
import json
import hashlib
import time
import sys
import traceback
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from minio import Minio
from io import BytesIO
import threading

sys.stdout.reconfigure(line_buffering=True)

# === CONFIG ===
REDPANDA = "redpanda:9092"
PII_FIELDS = ["license_plates"]

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


def get_minio():
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


# ========== TRAFFIC THREAD ==========
def traffic_governance():
    print("[TRAFFIC] Starting traffic governance thread...", flush=True)
    try:
        # Connect consumer
        print("[TRAFFIC] Connecting consumer...", flush=True)
        consumer = KafkaConsumer(
            "city.traffic.raw",
            bootstrap_servers=REDPANDA,
            value_deserializer=lambda m: json.loads(m.decode()),
            auto_offset_reset="earliest",
            group_id="gov-traffic-v5",
            consumer_timeout_ms=10000,
        )
        print("[TRAFFIC] Consumer connected", flush=True)

        # Connect producer
        producer = KafkaProducer(
            bootstrap_servers=REDPANDA,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        print("[TRAFFIC] Producer connected", flush=True)

        # Connect minio
        minio_client = get_minio()
        print("[TRAFFIC] MinIO connected", flush=True)

        print("[TRAFFIC] Listening for messages...", flush=True)

        while True:
            # Poll manually instead of iterator
            messages = consumer.poll(timeout_ms=5000)

            if not messages:
                print("[TRAFFIC] No messages, polling again...", flush=True)
                continue

            for topic_partition, records in messages.items():
                for msg in records:
                    raw = msg.value
                    governed, had_pii = govern_traffic(raw)

                    # Save raw
                    save_json(minio_client, "raw-zone", raw, "traffic")
                    # Save governed
                    save_json(minio_client, "curated-zone", governed, "traffic")
                    # Publish
                    producer.send("city.traffic.governed", value=governed)
                    producer.flush()

                    stats["traffic_processed"] += 1
                    if had_pii:
                        stats["pii_hashed"] += 1

                    print(
                        f"[TRAFFIC #{stats['traffic_processed']}] "
                        f"PII: {stats['pii_hashed']} | "
                        f"District: {raw.get('district')} | "
                        f"Plates: {raw.get('license_plates')}",
                        flush=True,
                    )

    except Exception as e:
        print(f"[TRAFFIC] CRASHED: {e}", flush=True)
        print(traceback.format_exc(), flush=True)


# ========== POLLUTION THREAD ==========
def pollution_governance():
    print("[POLLUTION] Starting pollution governance thread...", flush=True)
    try:
        consumer = KafkaConsumer(
            "city.pollution.raw",
            bootstrap_servers=REDPANDA,
            value_deserializer=lambda m: json.loads(m.decode()),
            auto_offset_reset="earliest",
            group_id="gov-pollution-v5",
            consumer_timeout_ms=10000,
        )
        print("[POLLUTION] Consumer connected", flush=True)

        producer = KafkaProducer(
            bootstrap_servers=REDPANDA,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        print("[POLLUTION] Producer connected", flush=True)

        minio_client = get_minio()
        print("[POLLUTION] MinIO connected", flush=True)

        print("[POLLUTION] Listening for messages...", flush=True)

        while True:
            messages = consumer.poll(timeout_ms=5000)

            if not messages:
                print("[POLLUTION] No messages, polling again...", flush=True)
                continue

            for topic_partition, records in messages.items():
                for msg in records:
                    raw = msg.value
                    governed = govern_pollution(raw)

                    save_json(minio_client, "curated-zone", governed, "pollution")
                    producer.send("city.pollution.governed", value=governed)
                    producer.flush()

                    stats["pollution_processed"] += 1
                    if governed.get("alert_level") in ["CRITICAL", "WARNING"]:
                        stats["alerts_triggered"] += 1

                    print(
                        f"[POLLUTION #{stats['pollution_processed']}] "
                        f"AQI: {raw.get('aqi')} | "
                        f"Alert: {governed.get('alert_level')} | "
                        f"District: {raw.get('district')}",
                        flush=True,
                    )

    except Exception as e:
        print(f"[POLLUTION] CRASHED: {e}", flush=True)
        print(traceback.format_exc(), flush=True)


# ========== STATS THREAD ==========
def print_stats():
    while True:
        time.sleep(30)
        print(f"\n{'=' * 60}", flush=True)
        print(f"STATS @ {datetime.utcnow().isoformat()}", flush=True)
        print(
            f"  Traffic:   {stats['traffic_processed']} processed, "
            f"{stats['pii_hashed']} PII hashed",
            flush=True,
        )
        print(
            f"  Pollution: {stats['pollution_processed']} processed, "
            f"{stats['alerts_triggered']} alerts",
            flush=True,
        )
        print(f"{'=' * 60}\n", flush=True)


# ========== MAIN ==========
def main():
    print("=" * 60, flush=True)
    print("GOVERNANCE AGENT v3.0 — DEBUG MODE", flush=True)
    print(f"Time: {datetime.utcnow().isoformat()}", flush=True)
    print(f"Redpanda: {REDPANDA}", flush=True)
    print(f"PII Fields: {PII_FIELDS}", flush=True)
    print("=" * 60, flush=True)

    # Wait for Redpanda to be fully ready
    print("Waiting 10s for Redpanda to stabilize...", flush=True)
    time.sleep(10)

    t1 = threading.Thread(target=traffic_governance, daemon=True, name="traffic-thread")
    t2 = threading.Thread(
        target=pollution_governance, daemon=True, name="pollution-thread"
    )
    t3 = threading.Thread(target=print_stats, daemon=True, name="stats-thread")

    t1.start()
    print("Traffic thread started", flush=True)

    time.sleep(2)  # Stagger startup

    t2.start()
    print("Pollution thread started", flush=True)

    t3.start()
    print("Stats thread started", flush=True)

    # Keep alive and monitor threads
    while True:
        time.sleep(10)
        if not t1.is_alive():
            print("WARNING: Traffic thread is DEAD!", flush=True)
        if not t2.is_alive():
            print("WARNING: Pollution thread is DEAD!", flush=True)


if __name__ == "__main__":
    main()
