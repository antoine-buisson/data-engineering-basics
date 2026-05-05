import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer

BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "taxi-rides")
EVENTS_PER_SECOND = float(os.environ.get("EVENTS_PER_SECOND", "2"))

# Rough bounding box for New York City
LAT_MIN, LAT_MAX = 40.477, 40.917
LON_MIN, LON_MAX = -74.259, -73.700

STATUSES = ["completed"] * 14 + ["cancelled"] * 3 + ["in_progress"] * 3

producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})


def make_ride() -> dict:
    pickup_lat = random.uniform(LAT_MIN, LAT_MAX)
    pickup_lon = random.uniform(LON_MIN, LON_MAX)
    dropoff_lat = random.uniform(LAT_MIN, LAT_MAX)
    dropoff_lon = random.uniform(LON_MIN, LON_MAX)
    distance_km = round(
        ((dropoff_lat - pickup_lat) ** 2 + (dropoff_lon - pickup_lon) ** 2) ** 0.5
        * 111,
        2,
    )
    fare_usd = round(max(3.0, distance_km * random.uniform(1.8, 3.2)), 2)
    return {
        "ride_id": str(uuid.uuid4()),
        "driver_id": f"driver_{random.randint(1, 200):03d}",
        "passenger_id": f"passenger_{random.randint(1, 500):04d}",
        "pickup_lat": round(pickup_lat, 6),
        "pickup_lon": round(pickup_lon, 6),
        "dropoff_lat": round(dropoff_lat, 6),
        "dropoff_lon": round(dropoff_lon, 6),
        "distance_km": distance_km,
        "fare_usd": fare_usd,
        "status": random.choice(STATUSES),
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }


def delivery_report(err, msg):
    if err:
        print(f"[ERROR] delivery failed: {err}")


def main():
    print(f"Producing to {BOOTSTRAP_SERVERS} → topic '{TOPIC}' at {EVENTS_PER_SECOND}/s")
    interval = 1.0 / EVENTS_PER_SECOND
    count = 0
    while True:
        ride = make_ride()
        producer.produce(
            TOPIC,
            key=ride["ride_id"],
            value=json.dumps(ride).encode(),
            callback=delivery_report,
        )
        producer.poll(0)
        count += 1
        if count % 20 == 0:
            print(f"[{datetime.now().isoformat(timespec='seconds')}] {count} events sent")
        time.sleep(interval)


if __name__ == "__main__":
    main()
