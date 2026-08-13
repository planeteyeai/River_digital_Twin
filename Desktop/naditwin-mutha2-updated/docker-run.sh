#!/bin/bash

# Build the Docker image
echo "Building NadiTwin Demo Docker image..."
docker build -t naditwin-demo .

# Run the container
echo "Starting NadiTwin Demo..."
docker run -d \
  --name naditwin-demo \
  -p 8080:8080 \
  --restart unless-stopped \
  naditwin-demo

echo "NadiTwin Demo is running at http://localhost:8080"
echo "To stop: docker stop naditwin-demo"
echo "To remove: docker rm naditwin-demo"