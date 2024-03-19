# ISS Tracker Web Application

## Overview
The ISS Tracker Web Application is a Flask-based web service that allows users to track the real-time position of the International Space Station (ISS). The app provides various endpoints to retrieve the current location, speed, and other telemetry data of the ISS, as well as running statistical computations on historical ISS position data.

### Important Files
- `iss_tracker.py`: The main Flask application script.
- `test_iss_tracker.py`: Contains unit tests for the application.
- `Dockerfile`: Instructions for Docker to build the application's container.

## Data Citation
The trajectory data is sourced from NASA's "Spot the Station" website, which offers comprehensive information about the ISS's orbit. The data can be found in two formats: XML or .txt. Press on this [link](https://spotthestation.nasa.gov/trajectory_data.cfm) to find the type of data you'd like to download.

### Accessing the Data
* The data can be obtained from the ISS Trajectory Data website listed above
* It is available in two formats: `.txt` and XML
* Significance of the data can be found on the website

## Deployment Instructions
To deploy the app with Docker Compose, follow these steps:
1. Clone the repository and navigate to the directory containing `docker-compose.yml`.
2. Run the command:
   ```
   docker-compose up --build
   ```
   This command builds the Docker image and starts the container.
3. The app will be accessible at `http://localhost:5000`.

## API Endpoints and Outputs
- `GET /now`: Returns the current location of the ISS.
  ```
  curl http://localhost:5000/now
  ```
  Output: JSON with the current latitude, longitude, and altitude of the ISS.

- `GET /epochs`: Lists all available epochs of the ISS position data.
  ```
  curl http://localhost:5000/epochs
  ```
  Output: JSON array of epochs.

- `GET /epochs/<epoch>`: Retrieves the ISS location for a specified epoch.
  ```
  curl http://localhost:5000/epochs/2024-02-23T00:00:00Z
  ```
  Output: JSON with the latitude, longitude, and altitude for the specified epoch.

- `GET /epoch/<epoch>/speed`: Gets the speed of the ISS at the specified epoch.
  ```
  curl http://localhost:5000/epoch/2024-02-23T00:00:00Z/speed
  ```
  Output: Plain text with the speed value.

## Running Containerized Unit Tests
To run the unit tests in the containerized environment, execute:
```
docker exec -it [container_id] pytest /app/test_iss_tracker.py
```
Replace `[container_id]` with the actual ID of the running container. You can find it by running `docker ps`.

Expected output will show the test results, indicating pass or fail statuses for each test case.
