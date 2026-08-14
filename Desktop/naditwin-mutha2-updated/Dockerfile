# NadiTwin Demo - River monitoring dashboard
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Debug: List what was copied
RUN echo "=== DEBUG: Contents of /app ===" && ls -la /app
RUN echo "=== DEBUG: Looking for run.py ===" && find /app -name "run.py" -type f
RUN echo "=== DEBUG: Current directory structure ===" && find /app -type f | head -20

# Create data directory if it doesn't exist
RUN mkdir -p data

# Expose port
EXPOSE 8080

# Health check (disabled for debugging)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8080/api/meta || exit 1

# Default command - use the launcher script
CMD ["python3", "start.py"]