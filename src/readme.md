
# Image Download and Prediction using UP42

This project allows you to download satellite images using UP42 API and process them in parallel. The downloaded images are saved in the `src/resources/download_images` directory, and processed images will be saved in `src/resources/predicted_image`. Meta data includes date and coordinates of image is saved in `src/resources/history.csv`.

## Setup and Usage

### Requirements

- Docker
- Python 3.x
- UP42 account and credentials, credentials should be saved in `src/.up42/credentials.json`
`e.g. {username:"username", password:"pwd"}`

### Environment Variables

- `DATE_FROM` - The start date for the satellite images (format: YYYY-MM-DD).
- `DATE_TO` - The end date for the satellite images (format: YYYY-MM-DD).
- `CONFIG_PATH` - The path to `coordinates.json` containing coordinates.

### Build the Docker Image

```bash
docker build -t marine_litter-image .

### Build the Docker Image

```bash
docker run -e DATE_FROM="2023-01-01" -e DATE_TO="2023-12-31" -e CONFIG_PATH="/marine_litter/src/resources/config.json"  -v "$(pwd)/src/.up42/credentials.json:/marine_litter/src/.up42/credentials.json" -v "$(pwd)/src/resources:/marine_litter/src/resources" marine_litter-image

```bash
docker run marine_litter-image python src/prediction.py

