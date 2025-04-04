#!/bin/bash

# Build the Docker image using the Dockerfile in the client directory
docker build -t my-python-dev ./client

# Run the container, mounting the client directory
docker run --rm -it -v "$(pwd)/client":/app -w /app my-python-dev
