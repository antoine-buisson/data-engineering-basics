FROM apache/flink:1.18.1-scala_2.12-java11

RUN wget -q -P /opt/flink/lib \
    https://repo1.maven.org/maven2/org/apache/flink/flink-shaded-hadoop-2-uber/2.8.3-10.0/flink-shaded-hadoop-2-uber-2.8.3-10.0.jar && \
    wget -q -P /opt/flink/lib \
    https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar && \
    wget -q -P /opt/flink/lib \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-1.18/1.5.2/iceberg-flink-runtime-1.18-1.5.2.jar && \
    wget -q -P /opt/flink/lib \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.5.2/iceberg-aws-bundle-1.5.2.jar

COPY submit-job.sh /opt/flink/bin/submit-job.sh
RUN chmod +x /opt/flink/bin/submit-job.sh

COPY job.sql /opt/flink/job.sql
