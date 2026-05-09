FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY .env .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "python scripts/seed_db.py && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
