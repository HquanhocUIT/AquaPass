FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/AquaPass/backend

WORKDIR /workspace/AquaPass

COPY backend/requirements.txt /workspace/AquaPass/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /workspace/AquaPass/backend/requirements.txt

# Keep the repository layout inside the image because the API reads the
# versioned demo catalog and migrations relative to the project root.
COPY backend /workspace/AquaPass/backend
COPY data /workspace/AquaPass/data

WORKDIR /workspace/AquaPass/backend
EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
