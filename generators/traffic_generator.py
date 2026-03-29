# generators/traffic_generator.py
import json
import time
import random
import string
from datetime import datetime
from kafka import KafkaProducer


def random_plate():
    """Generate a fake license plate"""
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    nums = "".join(random.choices(string.digits, k=4))
    end = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"{letters}-{nums}-{end}"


def create_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers="redpanda:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            print("Connected to Redpanda!")
            return producer
        except Exception as e:
            print(f"Waiting... {e}")
            time.sleep(3)


def main():
    producer = create_producer()
    districts = ["Sector-1", "Sector-2", "Sector-3", "Sector-4", "Sector-5"]
    count = 0

    while True:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "sensor_id": f"CAM-{random.randint(100, 999)}",
            "district": random.choice(districts),
            "vehicle_count": random.randint(5, 120),
            "avg_speed_kmh": round(random.uniform(15, 75), 1),
            "license_plates": [random_plate() for _ in range(random.randint(1, 4))],
        }

        producer.send("city.traffic.raw", value=event)
        count += 1
        print(
            f"[{count}] Sent | {event['district']} | "
            f"Vehicles: {event['vehicle_count']} | "
            f"Plates: {event['license_plates']}"
        )
        time.sleep(2)


if __name__ == "__main__":
    main()
