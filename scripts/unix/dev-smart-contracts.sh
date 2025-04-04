#!/bin/bash

# Build from smart-contracts
docker build -t smart-contract-dev ./smart-contracts

# Mount smart-contracts
docker run --rm -it -v "$(pwd)/smart-contracts":/app -w /app smart-contract-dev
