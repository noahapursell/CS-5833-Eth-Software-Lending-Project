# CS-5833-Eth-Software-Lending-Project

## Development

This project uses Docker to provide a consistent Python development environment.

### Setup Instructions

1. Install and start Docker:
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and Mac
   - `docker` package for Linux distributions

2. To build and start the development container:

- **On Linux or Mac (Unix systems)**:

  ```bash
  ./scripts/unix/run.sh
  ```

- **On Windows (Command Prompt)**:

  ```bat
  scripts.windows\run.bat
  ```

This will:

- Build the Docker image if it has not been built yet
- Mount your project directory into the container
- Start a bash shell inside the container, ready to run Python commands

### Notes

- Files edited on the host machine are immediately available inside the container.
- When you exit the container (`exit` or `Ctrl+D`), it will automatically clean up.
- To add new Python dependencies, update `requirements.txt` and rebuild the image.
