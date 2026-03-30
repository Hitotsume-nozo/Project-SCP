# security/load_test.py
"""
Pipeline throughput benchmark.
Measures how many records the governance agent can process per second.
"""

import json
import time
import sys
import random
import string
from kafka import KafkaProducer, KafkaConsumer

sys.stdout.reconfigure(line_buffering=True)


def random_plate():
    letters = "".join(random.choices(string.ascii_uppercase, k=2))
    nums = "".join(random.choices(string.digits, k=4))
    end = "".join(random.choices(string.ascii_uppercase, k=2))
    return f"{letters}-{nums}-{end}"


def generate_batch(size):
    districts = ["Sector-1", "Sector-2", "Sector-3", "Sector-4", "Sector-5"]
    return [
        {
            "timestamp": f"2025-01-01T00:00:{i:02d}",
            "sensor_id": f"CAM-{random.randint(100, 999)}",
            "district": random.choice(districts),
            "vehicle_count": random.randint(5, 120),
            "avg_speed_kmh": round(random.uniform(15, 75), 1),
            "license_plates": [random_plate() for _ in range(random.randint(1, 5))],
        }
        for i in range(size)
    ]


def run_load_test():
    print("=" * 60)
    print("PIPELINE LOAD TEST")
    print("=" * 60)

    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
    )

    batch_sizes = [50, 100, 200, 500]

    results = []

    for batch_size in batch_sizes:
        batch = generate_batch(batch_size)

        print(f"\nSending {batch_size} records...", end=" ")

        start = time.time()
        for record in batch:
            producer.send("city.traffic.raw", value=record)
        producer.flush()
        elapsed = time.time() - start

        rate = batch_size / elapsed
        results.append(
            {
                "batch_size": batch_size,
                "time_seconds": round(elapsed, 3),
                "records_per_second": round(rate, 1),
            }
        )

        print(f"Done in {elapsed:.3f}s ({rate:.1f} records/sec)")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"{'Batch Size':<15} {'Time (s)':<15} {'Throughput (rec/s)':<20}")
    print("-" * 50)
    for r in results:
        print(
            f"{r['batch_size']:<15} {r['time_seconds']:<15} {r['records_per_second']:<20}"
        )
    print("=" * 60)

    avg_throughput = sum(r["records_per_second"] for r in results) / len(results)
    print(f"\nAverage throughput: {avg_throughput:.1f} records/second")
    print(f"Estimated daily capacity: {avg_throughput * 86400:,.0f} records/day")


if __name__ == "__main__":
    run_load_test()
