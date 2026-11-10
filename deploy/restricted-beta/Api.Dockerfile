# Reuse validated installed dependencies, not the staging application/bootstrap.
FROM ai-effect-staging-api:0458b93949a4 AS installed
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
ARG PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.revision=$PORTAL_SOURCE_COMMIT
COPY --from=installed /usr/local /usr/local
COPY deploy/staging/build/requirements.lock /tmp/requirements.lock
RUN --network=none python -c "import importlib.metadata as m,re; text=open('/tmp/requirements.lock').read(); pins=re.findall(r'^([A-Za-z0-9_.-]+)==([^ \\n]+)',text,re.M); assert pins; assert all(m.version(n)==v for n,v in pins)" \
    && python -m pip check
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /app /service-contracts && chown app:app /app /service-contracts
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --chown=app:app apps/api/app ./app
COPY --chown=app:app deploy/migrations /opt/release/migrations
USER app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
