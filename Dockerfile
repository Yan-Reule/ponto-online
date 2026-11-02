FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000 TF_CPP_MIN_LOG_LEVEL=2 DEEPFACE_HOME=/models
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY main.py ./
COPY --from=frontend /build/dist frontend/dist/
EXPOSE 8000
CMD ["python", "main.py"]
