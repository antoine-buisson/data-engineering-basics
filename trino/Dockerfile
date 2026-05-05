FROM trinodb/trino:446
USER root
COPY etc /etc/trino
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R trino:trino /etc/trino
USER trino
ENTRYPOINT ["/entrypoint.sh"]
