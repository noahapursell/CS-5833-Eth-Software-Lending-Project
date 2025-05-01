# CS-5833-Eth-Software-Lending-Project

**Authors**: Nima Najafian & Noah Pursell

## Overview

This project is a decentralized software lending platform built as part of CS-5833. It demonstrates how Ethereum smart contracts, Dockerized development environments, and client-server interactions can be used to manage software licensing in a permissionless, programmable way.

The platform includes:

- A smart-contract system for renting and purchasing software (games)
- A Dockerized client interface for interacting with the platform
- Development tooling for rapid iteration on both client and smart-contract layers

📄 **[Read the full project report](./LimeLendReport.pdf)** for a detailed explanation of the architecture, design decisions, and implementation.

**[Watch a demonstration of the LimeLend Client](https://www.youtube.com/watch?v=v7LRLdV4ukY)**

<iframe width="560" height="315" src="https://www.youtube.com/embed/v7LRLdV4ukY" frameborder="0" allowfullscreen></iframe>

## Deployment

### Smart-Contracts Deployment

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

2. To build and start the production container (from the top directory):

- **On Linux or Mac (Unix systems)**:

  ```bash
  ./scripts/unix/deploy-smart-contracts.sh
  ```

- **On Windows (Command Prompt)**:

  ```bat
  scripts\windows\deploy-smart-contracts.bat
  ```

This will:

- Build the Docker image if it has not been built yet
- Deploy one container to run the HardHat ETH Network
- Deploy a second container that uses the HardHat Ignition Framework to deploy the GameRental smart-contract

### Client Deployment

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

1. To build and start the production container (from the top directory):
   - **On Linux or Mac (Unix systems)**:

     ```bash
     ./scripts/unix/dev-client.sh
     ```

   - **On Windows (Command Prompt)**:

     ```bat
     scripts\windows\dev-client.bat
     ```

3. Run the client with `python game_launcher.py`.

## Development

This project uses Docker to provide a consistent Python development environment.

### Setup Instructions

#### Client

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

2. To build and start the development container (from the top directory):

- **On Linux or Mac (Unix systems)**:

  ```bash
  ./scripts/unix/dev-client.sh
  ```

- **On Windows (Command Prompt)**:

  ```bat
  scripts\windows\dev-client.bat
  ```

This will:

- Build the Docker image if it has not been built yet
- Mount your project directory into the container
- Start a bash shell inside the container, ready to run Python commands

#### Smart-Contracts Development

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

2. To build and start the development container (from the top directory):

- **On Linux or Mac (Unix systems)**:

  ```bash
  ./scripts/unix/dev-smart-contracts.sh
  ```

- **On Windows (Command Prompt)**:

  ```bat
  scripts\windows\dev-smart-contracts.bat
  ```

This will:

- Build the Docker image if it has not been built yet
- Mount your project directory into the container
- Start a bash shell inside the container, ready to run npm/npx commands

### Notes

- Files edited on the host machine are immediately available inside the container.
- When you exit the container (`exit` or `Ctrl+D`), it will automatically clean up.
- To add new Python dependencies, update `requirements.txt` and rebuild the image.
