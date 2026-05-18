FROM python:3.11-slim

WORKDIR /app

# System deps for numpy/pandas build wheels
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    fastapi uvicorn[standard] python-multipart

# Copy entire repo so demo_data, models, etc. are importable
COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
