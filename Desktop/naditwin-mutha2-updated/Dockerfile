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

# Default command - try to find run.py
CMD if [ -f "run.py" ]; then python3 run.py --port 8080 --no-browser; elif [ -f "Desktop/naditwin-mutha2-updated/run.py" ]; then cd Desktop/naditwin-mutha2-updated && python3 run.py --port 8080 --no-browser; else echo "Cannot find run.py anywhere!" && find /app -name "*.py" && exit 1; fi