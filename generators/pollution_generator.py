# generators/pollution_generator.py
import json
import time
import random
import sys
from datetime import datetime
from kafka import KafkaProducer

sys.stdout.reconfigure(line_buffering=True)


def create_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers="redpanda:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print("Pollution generator connected!", flush=True)
            return producer
        except Exception as e:
            print(f"Waiting... {e}", flush=True)
            time.sleep(3)


def main():
    producer = create_producer()
    districts = ["Sector-1", "Sector-2", "Sector-3", "Sector-4", "Sector-5"]
    count = 0

    # Base pollution levels per district (some are worse)
    district_base = {
        "Sector-1": {"pm25": 45, "aqi": 80},
        "Sector-2": {"pm25": 120, "aqi": 200},  # Industrial area
        "Sector-3": {"pm25": 65, "aqi": 110},
        "Sector-4": {"pm25": 200, "aqi": 350},  # DANGER ZONE
        "Sector-5": {"pm25": 35, "aqi": 60},  # Clean area
    }

    while True:
        district = random.choice(districts)
        base = district_base[district]

        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "sensor_id": f"AQ-{random.randint(100, 999)}",
            "district": district,
            "pm25": round(base["pm25"] + random.uniform(-20, 30), 2),
            "pm10": round(base["pm25"] * 1.8 + random.uniform(-10, 40), 2),
            "aqi": int(base["aqi"] + random.uniform(-30, 40)),
            "co2_ppm": round(random.uniform(380, 650), 1),
            "temperature_c": round(random.uniform(25, 42), 1),
            "humidity_pct": round(random.uniform(30, 85), 1),
        }

        producer.send("city.pollution.raw", value=event)
        count += 1

        # Flag dangerous readings
        danger = (
            " DANGER"
            if event["aqi"] > 300
            else " WARNING"
            if event["aqi"] > 150
            else " OK"
        )

        print(
            f"[{count}] {district} | AQI: {event['aqi']} "
            f"| PM2.5: {event['pm25']} | {danger}",
            flush=True,
        )

        time.sleep(3)


if __name__ == "__main__":
    main()
