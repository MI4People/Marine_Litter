_This file holds the Docker related information—in addition to the project root 'README.md'._

## Docker Setup and Usage

### Requirements
- Docker
- Python version as in root 'pyproject.toml'
- UP42 account and credentials like `{username:"user", password:"pwd"}` in 'secrets/up42_credentials.json'
- Google credentials in 'secrets/google_credentials.json'
- a PyTorch model checkpoint in `~/.cache/torch/hub/checkpoints/`

#### Windows Setup
For transparently mounting the torch hub cache ('~/...'), before running Docker, set the `HOME` environment variable, like
`set HOME=%USERPROFILE%`, or permanently using PowerShell:
```powershell
[System.Environment]::SetEnvironmentVariable('HOME', "$env:USERPROFILE", 'User')
```

### Environment Variables
See './.example.env' for reference of the whole list
- `ML_CONFIG_PATH`: GeoJSON to configure UP42 downloads
- `ML_ORDER_WORKERS`: Number of parallel workers for UP42 downloads
- `ML_PREDICT_WORKERS`: Number of parallel workers for prediction
- `ML_DEVICE`: 'cpu' or 'cuda', for prediction


### Build and Run the Docker Image, Run Scripts in the Container
Ensure the project root 'uv.lock' is tested before `docker build`:
```bash
uv sync --active --upgrade
uv run pytest tests/
```
Note `UV_NO_DEV=true` in Dockerfile avoids installing dev dependencies despite `uv.lock` is fix.
Then you can build the image (from project root to take .dockerignore into account) like:
```bash
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile -t marine_litter .
```

Ensure your local, git-ignored `.env` and `secrets/*.json` files exist before running the image.

Run it interactively with mounted secrets and environment variables, like in next examples.
Do not prepend `uv run` as might be needed in other setups, since venv is added to PATH.
```bash
docker run -it --rm --gpus=all --env-file .env -v ./secrets:/marine_litter/secrets:ro marine_litter

# In the running container, check installation and settings:
gdalinfo --version && python --version && uv --version
python -c "import torch; print(f'torch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
ls -l /root/.cache/torch/hub/checkpoints
python scripts/run_all.py --help
python scripts/run_all.py --dry-run
```

Or run it as **one-off command** like:
```bash
# check installation and settings
docker run --rm --gpus=all --env-file .env -v ./secrets:/marine_litter/secrets:ro marine_litter python scripts/run_all.py --dry-run
```
which .
### Server requirements:
- Install NVIDIA driver (was done by Bechtle)
- Install Docker: https://docs.docker.com/engine/install/ubuntu/
- Install Toolkit to use CUDA in container: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

### Set up a routine running on server
```bash
git clone https://github.com/MI4People/Marine_Litter /home/demo1/marine_litter_project/marine_litter
cd marine_litter_project/marine_litter

docker/docker-compose build

crontab -e

0 2 * * * cd /home/demo1/marine_litter_project/marine_litter && docker-compose up && docker-compose logs > /home/demo1/marine_litter_project/logs/docker_logs_$(date +\%Y-\%m-\%d_\%H-\%M-\%S).log 2>&1
0 10 * * * cd /home/demo1/marine_litter_project/marine_litter && docker-compose down
```

### Optional testing environment with conda
Run the following in the terminal, preferably in your project root:
1. conda create --name marine_litter  # python version could also be specified
2. conda activate marine_litter
3. conda install -c conda-forge gdal
4. conda install -c conda-forge up42-py
5. pip install marinedebrisdetector
