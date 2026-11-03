# The web demo (web/). Build from the repo root.
FROM python:3.12-slim
WORKDIR /app
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY data/operations_daily.parquet /tmp/
COPY web/ .
RUN python -c "import duckdb; duckdb.connect('operations.duckdb').execute(\"create table operations_daily as from '/tmp/operations_daily.parquet'\")" \
 && rm /tmp/operations_daily.parquet
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
