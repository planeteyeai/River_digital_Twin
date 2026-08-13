# NadiTwin Demo - River monitoring dashboard
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/meta || exit 1

# Default command
CMD ["python3", "run.py", "--port", "8080", "--no-browser"]