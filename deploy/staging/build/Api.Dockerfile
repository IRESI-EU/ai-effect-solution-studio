FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS dependencies
COPY deploy/staging/build/requirements.lock /requirements.lock
COPY --from=locked_inputs /wheels /wheels
RUN --network=none python -m pip install --no-index --no-cache-dir --require-hashes --find-links=/wheels -r /requirements.lock \
    && python -m pip check

FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS source
COPY apps/api/app /source/app
RUN rm -rf /source/app/tests

FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS runtime
ARG PORTAL_SOURCE_COMMIT
LABEL org.opencontainers.image.revision=$PORTAL_SOURCE_COMMIT
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=dependencies /usr/local /usr/local
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /app /service-contracts && chown app:app /app /service-contracts
WORKDIR /app
COPY --from=source --chown=app:app /source/app ./app
COPY --chown=app:app deploy/migrations /opt/staging/migrations
COPY --chown=app:app deploy/staging/synthetic_seed.py /opt/staging/synthetic_seed.py
USER app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
