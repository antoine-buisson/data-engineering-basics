#!/bin/bash
set -e
# Write the Iceberg catalog config with credentials resolved from env vars
cat > /etc/trino/catalog/iceberg.properties <<EOF
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://iceberg-rest:8181
iceberg.rest-catalog.warehouse=s3://warehouse/
hive.s3.endpoint=http://minio:9000
hive.s3.path-style-access=true
hive.s3.aws-access-key=${AWS_ACCESS_KEY_ID}
hive.s3.aws-secret-key=${AWS_SECRET_ACCESS_KEY}
hive.s3.region=${AWS_REGION}
EOF
exec /usr/lib/trino/bin/run-trino
