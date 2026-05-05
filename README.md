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
| BI tool | Metabase |

## Quick start

**1. Configure credentials**

```bash
cp .env.example .env
# Edit .env if you want to change the default passwords
```

**2. Start the stack**

```bash
docker compose up -d
```

All services start in the correct dependency order via Docker healthchecks.  
The first run downloads Flink connector JARs (~200 MB) — allow a few minutes.

**3. Open the dashboard**

Once `metabase-init` completes (watch with `docker compose logs -f metabase-init`):

- **Metabase dashboard** → http://localhost:3000/dashboard/2  
  Login: values from `MB_ADMIN_EMAIL` / `MB_ADMIN_PASSWORD` in `.env`

## Other endpoints

| Service | URL | Credentials |
|---|---|---|
| Metabase | http://localhost:3000 | see `.env` |
| Flink UI | http://localhost:8081 | — |
| MinIO console | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env` |
| Trino | http://localhost:8080 | — |

## Verify the pipeline

```bash
# Watch ride events being produced (~2/s)
docker compose logs -f generator

# Peek at raw Kafka messages
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic taxi-rides \
  --from-beginning \
  --max-messages 5

# Query Iceberg directly via Trino
docker compose exec trino trino --catalog iceberg --schema demo \
  --execute "SELECT status, count(*) AS rides, round(avg(fare_usd),2) AS avg_fare FROM rides GROUP BY status;"
```

## Tear down

```bash
docker compose down -v   # -v also removes MinIO/Kafka/Metabase data volumes
```
