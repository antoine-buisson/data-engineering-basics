-- Enable checkpointing so Iceberg commits happen every 30 seconds
SET 'execution.checkpointing.interval' = '30s';
SET 'execution.checkpointing.mode' = 'EXACTLY_ONCE';

-- Kafka source table (taxi ride events)
CREATE TABLE kafka_rides (
  ride_id       STRING,
  driver_id     STRING,
  passenger_id  STRING,
  pickup_lat    DOUBLE,
  pickup_lon    DOUBLE,
  dropoff_lat   DOUBLE,
  dropoff_lon   DOUBLE,
  distance_km   DOUBLE,
  fare_usd      DOUBLE,
  status        STRING,
  started_at    TIMESTAMP(3),
  WATERMARK FOR started_at AS started_at - INTERVAL '5' SECOND
) WITH (
  'connector'                    = 'kafka',
  'topic'                        = 'taxi-rides',
  'properties.bootstrap.servers' = 'kafka:9092',
  'properties.group.id'          = 'flink-iceberg-consumer',
  'scan.startup.mode'            = 'earliest-offset',
  'format'                       = 'json'
);

-- Register the Iceberg REST catalog backed by MinIO
CREATE CATALOG iceberg_catalog WITH (
  'type'                    = 'iceberg',
  'catalog-type'            = 'rest',
  'uri'                     = 'http://iceberg-rest:8181',
  'warehouse'               = 's3://warehouse/',
  'io-impl'                 = 'org.apache.iceberg.aws.s3.S3FileIO',
  's3.endpoint'             = 'http://minio:9000',
  's3.path-style-access'    = 'true',
  's3.access-key-id'        = 'minioadmin',
  's3.secret-access-key'    = 'minioadmin',
  's3.region'               = 'us-east-1'
);

-- Ensure the target database exists
CREATE DATABASE IF NOT EXISTS iceberg_catalog.demo;

-- Iceberg target table (partitioned by day)
CREATE TABLE IF NOT EXISTS iceberg_catalog.demo.rides (
  ride_id       STRING,
  driver_id     STRING,
  passenger_id  STRING,
  pickup_lat    DOUBLE,
  pickup_lon    DOUBLE,
  dropoff_lat   DOUBLE,
  dropoff_lon   DOUBLE,
  distance_km   DOUBLE,
  fare_usd      DOUBLE,
  status        STRING,
  started_at    TIMESTAMP(6),
  event_date    DATE
) PARTITIONED BY (event_date)
WITH (
  'write.format.default'    = 'parquet',
  'write.target-file-size-bytes' = '134217728'
);

-- Stream insert: Kafka → Iceberg
INSERT INTO iceberg_catalog.demo.rides
SELECT
  ride_id,
  driver_id,
  passenger_id,
  pickup_lat,
  pickup_lon,
  dropoff_lat,
  dropoff_lon,
  distance_km,
  fare_usd,
  status,
  started_at,
  CAST(started_at AS DATE) AS event_date
FROM kafka_rides;
