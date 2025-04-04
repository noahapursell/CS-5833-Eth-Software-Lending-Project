@echo off

:: Build the Docker image using the Dockerfile in the smart-contracts directory
docker build -t smart-contracts-dev .\smart-contracts

:: Run the container, mounting the smart-contracts directory
docker run --rm -it -v "%cd%\smart-contracts":/app -w /app smart-contracts-dev
