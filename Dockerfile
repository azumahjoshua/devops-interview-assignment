# Use a lightweight Python runtime
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure logs are written immediately
ENV PYTHONUNBUFFERED=1

# Application directory
WORKDIR /app

# Copy dependency definition first (better Docker layer caching)
COPY pyproject.toml .

# Copy source code
COPY src ./src

# Install the application and its dependencies
RUN pip install --no-cache-dir .

# Run the cleanup service
CMD ["python", "-m", "cleaner.main"]