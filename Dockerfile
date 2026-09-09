FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONTROL_GATE_DB_PATH=/data/runs.sqlite3

WORKDIR /app

RUN addgroup --system controlgate && adduser --system --ingroup controlgate controlgate

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[runtime,service]"

RUN mkdir /data && chown controlgate:controlgate /data
USER controlgate
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "control_gate.service:app", "--host", "0.0.0.0", "--port", "8000"]
