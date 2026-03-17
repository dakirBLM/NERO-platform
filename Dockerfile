# ── Base image ────────────────────────────────────────────────
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── System dependencies ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ── Copy project source ───────────────────────────────────────
COPY . .

# ── Collect static files ──────────────────────────────────────
RUN python manage.py collectstatic --noinput

# ── Expose port ───────────────────────────────────────────────
EXPOSE 8000

# ── Start with Gunicorn ───────────────────────────────────────
CMD ["gunicorn", "Nero_platform.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
