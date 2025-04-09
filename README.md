# CS-5833-Eth-Software-Lending-Project

## Deployment

### Smart-Contracts Deployment

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

2. To build and start the development container (from the top directory):

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
