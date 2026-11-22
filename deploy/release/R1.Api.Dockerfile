# Reuse the inspected, immutable installed dependency closure; copy NO old app.
FROM ai-effect-beta-candidate-api:002686f04fb5@sha256:22c4994a05dce43bde2472a20f73ee27605a955a28ae6085742364ad32d672be AS dependencies
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS source
COPY apps/api/app /source/app
RUN rm -rf /source/app/tests
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
ARG PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.revision=$PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.source="https://github.com/IRESI-EU/ai-effect-solution-studio"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_SCHEMA_MODE=validate DESIGN_AI_ENABLED=false
COPY --from=dependencies /usr/local /usr/local
COPY deploy/staging/build/requirements.lock /opt/r1/requirements.lock
RUN --network=none python -c "import importlib.metadata as m; s=open('/opt/r1/requirements.lock').read(); pins=[line.split()[0].split('==') for line in s.splitlines() if line and not line.startswith('#')]; assert pins; assert all(m.version(n)==v for n,v in pins)" \
    && python -m pip check \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /app /service-contracts && chown app:app /app /service-contracts
WORKDIR /app
COPY --chown=app:app --from=source /source/app ./app
COPY --chown=app:app deploy/migrations /opt/r1/migrations
USER app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
