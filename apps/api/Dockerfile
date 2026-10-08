FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /service-contracts \
    && chown -R app:app /app /service-contracts
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
