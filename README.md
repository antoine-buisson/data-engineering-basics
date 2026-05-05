# data-engineering-basics

A self-contained data engineering demo pipeline for presentations. Runs entirely on Docker Compose — no cloud account needed.

## Architecture

```
Python generator (taxi rides ~2/s)
        │
        ▼
Kafka (KRaft)  ──  topic: taxi-rides
        │
        ▼
Flink SQL job  (Kafka source → Iceberg sink)
        │
        ▼
Iceberg REST Catalog  ──►  MinIO (S3-compatible)
                                   │
                             warehouse/demo/rides/
        ▼
Trino  (iceberg connector)
        │
        ▼
Metabase  (dashboards)
```

## Stack

| Component | Technology |
|---|---|
| Event generator | Python 3.12 + confluent-kafka |
| Message broker | Kafka 3.7 (KRaft, no Zookeeper) |
| Stream processor | Apache Flink 1.18 (SQL) |
| Table format | Apache Iceberg 1.5 |
| Catalog | Iceberg REST catalog |
| Object storage | MinIO |
| Query engine | Trino 446 |
| BI tool | Metabase v0.50 |

## Quick start

```bash
docker compose up -d
```

All services start in the correct order via healthcheck dependencies.  
First startup downloads Flink connector JARs — allow a few minutes.

## Verify the pipeline

```bash
# Watch ride events being produced
docker compose logs -f generator

# Peek at raw Kafka messages
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic taxi-rides \
  --from-beginning \
  --max-messages 5

# Check Flink job status
open http://localhost:8081

# Browse Iceberg files in MinIO
open http://localhost:9001   # user: minioadmin / minioadmin

# Query with Trino
docker compose exec trino trino --catalog iceberg --schema demo
> SELECT status, count(*) AS rides, round(avg(fare_usd), 2) AS avg_fare
  FROM rides GROUP BY status;

# Open Metabase dashboard
open http://localhost:3000
```

## Metabase setup (first time)

1. Open http://localhost:3000 and complete the onboarding wizard.
2. Add a database → choose **Trino** (or **Starburst**).
3. Host: `trino`, Port: `8080`, Catalog: `iceberg`, Schema: `demo`.
4. Build questions / dashboards on the `rides` table.

## Tear down

```bash
docker compose down -v   # -v removes named volumes (MinIO data, Kafka data)
```
