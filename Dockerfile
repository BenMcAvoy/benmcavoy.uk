# Builder stage: build a wheel without leaving build deps in the runtime image
FROM python:3.13-slim AS builder
WORKDIR /app

# Install build tools only in the builder stage
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential \
	&& rm -rf /var/lib/apt/lists/*

# Copy project metadata first to leverage Docker layer caching
# Copy project metadata first to leverage Docker layer caching
# If you maintain a lock file (e.g. `poetry.lock`), consider adding it here
COPY pyproject.toml /app/

# Copy source and build a wheel into /dist
COPY . /app/
RUN pip install --upgrade pip build wheel setuptools \
	&& python -m build --wheel --outdir /dist

# Runtime stage: slim image with only runtime deps
FROM python:3.13-slim
WORKDIR /app

# Recommended environment variables for Python apps
ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

# Install the built wheel (no build deps needed)
COPY --from=builder /dist/*.whl /dist/
RUN pip install --no-cache-dir /dist/*.whl

# Copy application files (if your app needs static files or templates at runtime)
COPY . /app

# Expose the port the app listens on
EXPOSE 8000

# Default command (ensure `gunicorn` is in your project dependencies)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]