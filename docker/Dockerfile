FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.5
# This base image (https://github.com/OSGeo/gdal/tree/master/docker/) comes with
#   Ubuntu 24.04 LTS
#   Python 3.12.3
#   GDAL 3.11.5
# Keep the GDAL version in sync with .devcontainer/Dockerfile and the gdal pin in pyproject.toml.
#
# See parallel 'readme.md' for usage.

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

# g++ and python3-dev are needed to build the gdal Python bindings inside the venv (see pyproject.toml).
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget g++ python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Add venv to PATH so python can be called directly, and
# configure uv to avoid some CLI parameters (https://docs.astral.sh/uv/reference/cli/).
ENV PATH="/root/.local/bin:/marine_litter/.venv/bin:${PATH}" \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /marine_litter

RUN mkdir -p images/downloaded \
    && mkdir -p images/predicted \
    && mkdir -p secrets \
    && mkdir -p /root/.cache/torch/hub/checkpoints \
    && MODEL_CKPT='epoch=54-val_loss=0.50-auroc=0.987.ckpt' \
    && wget --no-check-certificate "http://dalic.de/mi4people/${MODEL_CKPT}" \
    && mv "${MODEL_CKPT}" /root/.cache/torch/hub/checkpoints/"${MODEL_CKPT}"

# NOTE, especially torch and cuda dependencies are huge, so we need to
# - use layering (to save `docker build` time)
# - keep the cache outside the Docker image (to save download time and image size)
# Dependencies (change less frequently)
COPY ../pyproject.toml .
COPY ../uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv .venv \
    && uv sync --frozen --no-install-project \
    && python -c "from osgeo import gdal, gdal_array; print(f'Python gdal: {gdal.__version__}')"

# Copy code (changes more frequently), and provide project
COPY ../LICENSE.txt .
COPY ../README.md .
COPY ../resources/ ./resources
COPY ../scripts/ ./scripts
COPY ../src/ ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["/bin/bash"]
