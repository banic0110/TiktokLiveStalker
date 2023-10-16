# TikTok Live Stalker

TikTok Live Stalker is a Python project that allows you to monitor TikTok live streams and collect data such as gifts and viewer connections. This project uses the TikTokLiveClient library to connect to TikTok live streams and a PostgreSQL database to store the collected data.

## Prerequisites

Before deploying this project, you need to have the following prerequisites in place:

- Python 3.x
- Docker (for containerization)
- Docker Compose (for managing multi-container applications)
- PostgreSQL database (you can set up a local database or use a cloud-based service)

## Project Structure

- `main.py`: The main Python script that connects to TikTok live streams, collects data, and stores it in the database.
- `Dockerfile`: The Dockerfile for building a Docker image of the project.
- `docker-compose.yml`: A Docker Compose file for defining the application's services and their configurations.
- `requirements.txt`: A file containing the Python dependencies required for the project.
