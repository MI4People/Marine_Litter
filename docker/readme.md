# Image Download and Prediction using UP42

This project allows you to download satellite images using UP42 API and process them in parallel. The downloaded images are saved in the `images/downloaded` directory, and processed images will be saved in `images/predicted`. Meta data includes date and coordinates of image is saved in `src/resources/dates.json`.

## Setup and Usage

### Requirements
- Docker
- Python 3.x
- UP42 account and credentials like `{username:"user", password:"pwd"}` in 'secrets/up42_credentials.json' 
- Google credentials in 'secrets/google_credentials.json'

### Environment Variables
- `CONFIG_PATH` - The path to 'coordinates.json' containing coordinates.

### Build and Run the Docker Image
Call (best from project root to take .dockerignore into account) Docker commands such as:
```bash
docker build -f docker/Dockerfile -t marine_litter .
docker run —-rm -e DAYS_BEFORE=2 -e ORDER_WORKERS=1 -e PREDICT_WORKERS=1 -e DEVICE=cpu marine_litter
```
or
```bash
docker build -f docker/osgeo.dockerfile --progress=plain -t ml_osgeo .
docker run —-rm -e DAYS_BEFORE=2 -e ORDER_WORKERS=8 -e PREDICT_WORKERS=4 -e DEVICE=cuda ml_osgeo
```
- ORDER_WORKERS: Number of parallel workers for ordering (download)
- PREDICT_WORKERS: Number of parallel workers for prediction
- DEVICE: cpu or cuda

### Sever requirements:
- Install NVIDIA driver (was done by Bechtle)
- Install Docker: https://docs.docker.com/engine/install/ubuntu/
- Install Toolkit to use CUDA in container: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

### Set up routine running on server
```bash
git clone https://github.com/MI4People/Marine_Litter /home/demo1/marine_litter_project/marine_litter
```

```bash
cd marine_litter_project/marine_litter
docker-compose build
```

```bash
crontab -e
```

```bash
0 2 * * * cd /home/demo1/marine_litter_project/marine_litter && docker-compose up && docker-compose logs > /home/demo1/marine_litter_project/logs/docker_logs_$(date +\%Y-\%m-\%d_\%H-\%M-\%S).log 2>&1
0 10 * * * cd /home/demo1/marine_litter_project/marine_litter && docker-compose down
```

### Optional testing environment with conda
Run the following in the terminal, preferably within your repo path:
1. conda create --name marine_litter (python version could also be specified)
2. conda activate marine_litter
3. conda install -c conda-forge gdal
4. conda install -c conda-forge up42-py
5. pip install marinedebrisdetector
6. make sure, that the file src/.up42/credentials.json exists, and is properly set with the correct credentials.
