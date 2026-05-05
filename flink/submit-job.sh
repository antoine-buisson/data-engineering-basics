#!/bin/bash
set -e

JOBMANAGER_URL="http://flink-jobmanager:8081"

echo "Waiting for Flink JobManager..."
until curl -sf "${JOBMANAGER_URL}/overview" > /dev/null; do
  sleep 3
done
echo "JobManager is up."

echo "Submitting Flink SQL job..."
/opt/flink/bin/sql-client.sh -f /opt/flink/job.sql

echo "Job submitted successfully."
