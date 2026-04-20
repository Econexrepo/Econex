FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
COPY relationship_table.csv /app/

EXPOSE 8000

# Entry point: backend/main.py defines `app = FastAPI(...)`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
