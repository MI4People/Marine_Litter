# Setup & Testing Guide — Docker Compose

> Step-by-step guide to build, configure, and test the Marine Litter pipeline using Docker.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Prepare Credentials](#3-prepare-credentials)
4. [Create the Environment File](#4-create-the-environment-file)
5. [Build the Docker Image](#5-build-the-docker-image)
6. [Test the Setup (Dry Run)](#6-test-the-setup-dry-run)
7. [Run the Full Pipeline](#7-run-the-full-pipeline)
8. [Run with Docker Compose](#8-run-with-docker-compose)
9. [Verify Results](#9-verify-results)
10. [Running Tests Inside Docker](#10-running-tests-inside-docker)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Software | Purpose | Install |
|----------|---------|---------|
| **Docker** (≥ 24.0) | Container runtime | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** (V2) | Container orchestration | Included with Docker Desktop, or [plugin install](https://docs.docker.com/compose/install/) |
| **Git** | Clone the repository | [git-scm.com](https://git-scm.com/) |

### Optional (for GPU support)

| Software | Purpose | Install |
|----------|---------|---------|
| **NVIDIA Driver** (≥ 535) | GPU access from host | [nvidia.com/drivers](https://www.nvidia.com/drivers/) |
| **NVIDIA Container Toolkit** | GPU access in Docker | [install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |

> **Note:** GPU support is optional. The pipeline runs on CPU-only machines (slower prediction ~10 min/TIF vs ~30s on GPU).

### Verify Docker Installation

```bash
docker --version
docker compose version
```

### Verify GPU Access (optional)

**Bash / Linux / macOS:**
```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

**PowerShell / Windows:**
```powershell
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/MI4People/Marine_Litter.git
cd Marine_Litter
```

---

## 3. Prepare Credentials

The pipeline requires two credential files. These are **git-ignored** and must be created manually.

### 3.1 UP42 Credentials

Create `secrets/up42_credentials.json` with your UP42 account credentials:

**Bash:**
```bash
mkdir -p secrets
```

**PowerShell:**
```powershell
New-Item -ItemType Directory -Force -Path secrets
```

Then create the file with this content:

```json
{
    "username": "your-up42-email@example.com",
    "password": "your-up42-password"
}
```

> **How to get UP42 credentials:**
> 1. Sign up at [console.up42.com](https://console.up42.com/)
> 2. Use your account email and password
> 3. Alternatively, create a project API key in the UP42 console

### 3.2 Google Cloud Storage Credentials

Create `secrets/google_credentials.json` with a GCS service account key:

1. Go to [Google Cloud Console → IAM → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a service account with **Storage Object Admin** role on the `marinelitter_predicted` bucket
3. Generate a JSON key and save it as `secrets/google_credentials.json`

> **For testing without real uploads:** You can skip this file — the pipeline will log an error at the upload stage but the prediction step will still work.

### Verify Files Exist

**Bash:**
```bash
ls -la secrets/
```

**PowerShell:**
```powershell
Get-ChildItem secrets/
```

Expected: `up42_credentials.json` and `google_credentials.json`

---

## 4. Create the Environment File

Copy the example and adjust values:

**Bash:**
```bash
cp .example.env .env
```

**PowerShell:**
```powershell
Copy-Item .example.env .env
```

Edit `.env` to match your setup:

```ini
### Marine Litter Configuration
### All settings use the ML_ prefix.

# Logging
ML_LOG_FORMAT='%(message)-100s |%(levelname).3s %(asctime)s %(filename)s:%(lineno)d'
ML_LOG_LEVEL=INFO

# Authentication
ML_GOOGLE_CREDS_PATH=secrets/google_credentials.json
ML_UP42_CREDS_PATH=secrets/up42_credentials.json

# Paths (these are paths INSIDE the container)
ML_CHECKPOINT_FILE='epoch=54-val_loss=0.50-auroc=0.987.ckpt'
ML_CHECKPOINTS='~/.cache/torch/hub/checkpoints/'
ML_DATES_PATH=resources/dates.json
ML_GEOJSON_PATH=resources/features.geojson
ML_INPUT_PATH=images/downloaded
ML_OUTPUT_PATH=images/predicted

# Processing
ML_BUCKET_NAME=marinelitter_predicted
ML_CLOUDS_PERC_MAX=42
ML_DAYS_BEFORE=3
ML_DAYS_NUM=1
ML_DEVICE=cpu              # Use 'cuda' if you have GPU support
ML_ORDER_WORKERS=2
ML_PREDICT_WORKERS=1       # Increase if you have multiple GPUs
ML_PRODUCT_NAME=sentinel-2-level-2a
```

> **Important:** Use `ML_DEVICE=cpu` for CPU-only machines, `ML_DEVICE=cuda` for GPU machines.

---

## 5. Build the Docker Image

Build from the **project root** (required for build context):

```bash
docker build -f docker/Dockerfile -t marine_litter .
```

**Expected output (first build ~5–10 min, depends on internet speed):**
```
 => [1/8] FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4
 => [2/8] COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
 => [3/8] RUN apt-get update ...
 => [4/8] RUN mkdir -p images/downloaded ...           # Downloads model checkpoint (~50 MB)
 => [5/8] COPY pyproject.toml .
 => [6/8] RUN uv venv ... && uv sync --frozen ...      # Installs PyTorch + deps (~3 GB)
 => [7/8] COPY ... ./src
 => [8/8] RUN uv sync --frozen
 => => naming to docker.io/library/marine_litter
```

> **Subsequent builds** are much faster due to Docker layer caching — only changed layers are rebuilt.

### Verify the Image

```bash
docker images marine_litter
# REPOSITORY      TAG       IMAGE ID       CREATED          SIZE
# marine_litter   latest    abc123def456   30 seconds ago   ~5 GB
```

---

## 6. Test the Setup (Dry Run)

The `--dry-run` flag validates configuration without placing any orders or making API calls.

> **Important:** Docker flags (like `--gpus`, `--env-file`, `-v`) must come **before** the image name `marine_litter`.

### 6.1 Quick Validation (no credentials needed)

**Bash:**
```bash
docker run --rm marine_litter \
    python -c "import torch; import marine_litter; from osgeo import gdal; \
    print(f'torch={torch.__version__}, GDAL={gdal.__version__}, CUDA={torch.cuda.is_available()}')"
```

**PowerShell:**
```powershell
docker run --rm marine_litter `
    python -c "import torch; import marine_litter; from osgeo import gdal; print(f'torch={torch.__version__}, GDAL={gdal.__version__}, CUDA={torch.cuda.is_available()}')"
```

**Expected output:**
```
torch=2.9.1+cu130, GDAL=3.11.4, CUDA=False
```
> CUDA=True if running with `--gpus all`

### 6.2 Check Model Checkpoint

**Bash:**
```bash
docker run --rm marine_litter \
    ls -lh /root/.cache/torch/hub/checkpoints/
```

**PowerShell:**
```powershell
docker run --rm marine_litter `
    ls -lh /root/.cache/torch/hub/checkpoints/
```

**Expected output:**
```
-rw-r--r-- 1 root root 50M ... epoch=54-val_loss=0.50-auroc=0.987.ckpt
```

### 6.3 Dry Run with Credentials

This validates the full settings loading + UP42 authentication.

**Bash:**
```bash
docker run --rm \
    --env-file .env \
    -v ./secrets:/marine_litter/secrets:ro \
    marine_litter \
    python scripts/run_all.py --dry-run
```

**PowerShell:**
```powershell
docker run --rm `
    --env-file .env `
    -v ./secrets:/marine_litter/secrets:ro `
    marine_litter `
    python scripts/run_all.py --dry-run
```

**Expected output (success):**
```
Settings:
Name              | Value                                  | Description
log_level         | INFO                                   | ...
device            | cpu                                    | Options: cpu|cuda
...
GDAL: 3.11.4
CUDA is not available!
========== Starting workflow
---------- Download scenes (images) from UP42
---------- Run prediction on images
---------- Upload and delete images
========== Workflow completed
```

### 6.4 Dry Run with GPU Support

**Bash:**
```bash
docker run --rm --gpus all \
    --env-file .env \
    -v ./secrets:/marine_litter/secrets:ro \
    marine_litter \
    python scripts/run_all.py --dry-run
```

**PowerShell:**
```powershell
docker run --rm --gpus all `
    --env-file .env `
    -v ./secrets:/marine_litter/secrets:ro `
    marine_litter `
    python scripts/run_all.py --dry-run
```

**Expected output (with GPU):**
```
CUDA: 13.0
  01: NVIDIA GeForce RTX 4080 SUPER (80 MPs, 16376 MB)
```

---

## 7. Run the Full Pipeline

> ⚠️ **Warning:** The full pipeline places real orders on UP42 (may incur costs) and uploads to GCS. Make sure your credentials and `.env` settings are correct.

### CPU-Only

**Bash:**
```bash
docker run --rm \
    --env-file .env \
    -v ./secrets:/marine_litter/secrets:ro \
    marine_litter \
    python scripts/run_all.py --log INFO
```

**PowerShell:**
```powershell
docker run --rm `
    --env-file .env `
    -v ./secrets:/marine_litter/secrets:ro `
    marine_litter `
    python scripts/run_all.py --log INFO
```

### With GPU

**Bash:**
```bash
docker run --rm --gpus all \
    --env-file .env \
    -v ./secrets:/marine_litter/secrets:ro \
    marine_litter \
    python scripts/run_all.py --log INFO
```

**PowerShell:**
```powershell
docker run --rm --gpus all `
    --env-file .env `
    -v ./secrets:/marine_litter/secrets:ro `
    marine_litter `
    python scripts/run_all.py --log INFO
```

### Run Individual Pipeline Steps

**Bash:**
```bash
# Step 1: Download satellite images from UP42
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/download_from_up42.py --log INFO

# Step 1b: Only search scenes, don't order (safe, no cost)
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/download_from_up42.py --log INFO --tell-only

# Step 2: Process ZIPs and run prediction
docker run --rm --gpus all --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/predict_litter.py

# Step 3: Upload predictions to Google Cloud Storage
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/upload_to_gc_storage.py
```

**PowerShell:**
```powershell
# Step 1: Download satellite images from UP42
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/download_from_up42.py --log INFO

# Step 1b: Only search scenes, don't order (safe, no cost)
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/download_from_up42.py --log INFO --tell-only

# Step 2: Process ZIPs and run prediction
docker run --rm --gpus all --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/predict_litter.py

# Step 3: Upload predictions to Google Cloud Storage
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/upload_to_gc_storage.py
```

---

## 8. Run with Docker Compose

### 8.1 Current docker-compose.yml

> ⚠️ **Known Issues:** The existing `docker/docker-compose.yml` has bugs (see TODOS.md: ML-014, ML-015).
> The env vars are missing the `ML_` prefix and the volume paths are hardcoded.
> Use the manual `docker run` commands from Step 7 until these are fixed,
> or create a corrected compose file as below.

### 8.2 Corrected Docker Compose (Recommended)

Create a `docker-compose.yml` in the **project root**:

```yaml
services:
  marine_litter:
    build:
      context: .
      dockerfile: docker/Dockerfile
    env_file:
      - .env
    volumes:
      - ./secrets:/marine_litter/secrets:ro
    command: python scripts/run_all.py --log INFO --dry-run

  # GPU variant — use: docker compose --profile gpu up
  marine_litter_gpu:
    extends:
      service: marine_litter
    profiles: ["gpu"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - ML_DEVICE=cuda
    command: python scripts/run_all.py --log INFO --dry-run
```

### 8.3 Run with Docker Compose

```bash
# CPU-only (dry run by default)
docker compose up --build

# With GPU
docker compose --profile gpu up --build
```

**Override the command (e.g. for the full pipeline):**

**Bash:**
```bash
docker compose run --rm marine_litter \
    python scripts/run_all.py --log INFO
```

**PowerShell:**
```powershell
docker compose run --rm marine_litter `
    python scripts/run_all.py --log INFO
```

**Interactive shell:**

```bash
docker compose run --rm marine_litter bash
```

### 8.4 Stop and Clean Up

```bash
docker compose down

# Remove the built image (to force a complete rebuild)
docker rmi marine_litter
```

---

## 9. Verify Results

### Check Downloaded Images

**Bash:**
```bash
docker run --rm \
    -v ./images:/marine_litter/images \
    marine_litter \
    ls -lh images/downloaded/
```

**PowerShell:**
```powershell
docker run --rm `
    -v ./images:/marine_litter/images `
    marine_litter `
    ls -lh images/downloaded/
```

### Check Predictions

**Bash:**
```bash
docker run --rm \
    -v ./images:/marine_litter/images \
    marine_litter \
    ls -lh images/predicted/
```

**PowerShell:**
```powershell
docker run --rm `
    -v ./images:/marine_litter/images `
    marine_litter `
    ls -lh images/predicted/
```

### Check Dates JSON

**Bash:**
```bash
docker run --rm marine_litter \
    cat resources/dates.json | python -m json.tool | head -20
```

**PowerShell:**
```powershell
docker run --rm marine_litter `
    python -c "import json; print(json.dumps(json.load(open('resources/dates.json')), indent=2)[:500])"
```

---

## 10. Running Tests Inside Docker

The Docker image doesn't include dev dependencies by default (`UV_NO_DEV=1`).
To run tests, enter an interactive shell and install them:

**Bash:**
```bash
docker run --rm -it marine_litter bash

# Inside the container:
UV_NO_DEV=0 uv sync --frozen
python -m pytest tests/ -v --tb=short
```

**PowerShell:**
```powershell
docker run --rm -it marine_litter bash

# Inside the container (same commands — you're now in a Linux shell):
UV_NO_DEV=0 uv sync --frozen
python -m pytest tests/ -v --tb=short
```

> **Note:** The test `test_run_prediction_on_file` requires CUDA and will be skipped on CPU-only machines.

---

## 11. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| `"--gpus": executable file not found` | `--gpus` placed **after** the image name | Docker flags must come **before** the image name: `docker run --gpus all marine_litter ...` |
| `"\\": executable file not found` | Backslash `\` line continuation in PowerShell | Use backtick `` ` `` instead of `\`, or put the command on a single line |
| `CUDA is not available!` | No GPU or missing toolkit | Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) and use `--gpus all` |
| `Failed to load credentials` | Missing or malformed JSON | Check `secrets/up42_credentials.json` format |
| `FileNotFoundError: .env` | No `.env` file | Copy `.example.env` to `.env` |
| `Settings silently ignored` | Env vars missing `ML_` prefix | All env vars must start with `ML_` (e.g. `ML_DEVICE`, not `DEVICE`) |
| `Permission denied` on secrets | Volume mount issue | Use `:ro` suffix and ensure files are readable |
| Build fails at `uv sync` | Network issues | Retry; PyTorch wheels are ~2 GB |
| `wget: unable to resolve host` | DNS issue in Docker | Add `--network=host` to build or configure Docker DNS |
| Very slow prediction on CPU | Expected behavior | Use GPU (`ML_DEVICE=cuda`) or reduce image count |

### Docker Command Syntax Reminder

```
docker run [OPTIONS] IMAGE [COMMAND] [ARGS...]
             ▲        ▲       ▲
             │        │       └── e.g. python scripts/run_all.py
             │        └────────── e.g. marine_litter
             └─────────────────── e.g. --rm --gpus all --env-file .env
```

> **All flags go BEFORE the image name.** Anything after the image name is treated as the command to run inside the container.

### Line Continuation Reference

| Shell | Continuation character | Example |
|-------|----------------------|---------|
| **Bash** / Linux / macOS | `\` (backslash) | `docker run --rm \`<br>`  marine_litter python ...` |
| **PowerShell** / Windows | `` ` `` (backtick) | ``docker run --rm ` ``<br>`  marine_litter python ...` |
| **cmd.exe** / Windows | `^` (caret) | `docker run --rm ^`<br>`  marine_litter python ...` |

### Inspect Container State

**Bash:**
```bash
docker run --rm -it --env-file .env \
    -v ./secrets:/marine_litter/secrets:ro \
    marine_litter bash
```

**PowerShell:**
```powershell
docker run --rm -it --env-file .env `
    -v ./secrets:/marine_litter/secrets:ro `
    marine_litter bash
```

Once inside the container:
```bash
# These commands are the same on all platforms (you're in a Linux container)
python --version                    # Python 3.12.3
gdalinfo --version                  # GDAL 3.11.4
uv --version
python -c "import torch; print(torch.__version__)"
python -c "from marine_litter.ml_settings import MLSettings; print(MLSettings().as_table())"
ls -la secrets/
ls -la /root/.cache/torch/hub/checkpoints/
```

### View Logs (Docker Compose)

```bash
# Follow live logs
docker compose logs -f marine_litter
```

Save logs to file:

**Bash:**
```bash
docker compose logs marine_litter > pipeline_$(date +%Y-%m-%d).log 2>&1
```

**PowerShell:**
```powershell
docker compose logs marine_litter > "pipeline_$(Get-Date -Format 'yyyy-MM-dd').log" 2>&1
```

### Disk Space

The Docker image is approximately **5 GB** due to PyTorch + CUDA runtime. Ensure sufficient disk space:

```bash
docker system df
# Clean up unused images/containers if needed
docker system prune
```

---

## Quick Reference

**Bash:**
```bash
# Build + dry-run test (CPU)
docker build -f docker/Dockerfile -t marine_litter . && \
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/run_all.py --dry-run

# Build + dry-run test (GPU)
docker build -f docker/Dockerfile -t marine_litter . && \
docker run --rm --gpus all --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/run_all.py --dry-run

# Tell-only (search scenes, no ordering, safe)
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro \
    marine_litter python scripts/download_from_up42.py --tell-only --log INFO
```

**PowerShell:**
```powershell
# Build + dry-run test (CPU)
docker build -f docker/Dockerfile -t marine_litter .
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/run_all.py --dry-run

# Build + dry-run test (GPU)
docker build -f docker/Dockerfile -t marine_litter .
docker run --rm --gpus all --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/run_all.py --dry-run

# Tell-only (search scenes, no ordering, safe)
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro `
    marine_litter python scripts/download_from_up42.py --tell-only --log INFO
```
