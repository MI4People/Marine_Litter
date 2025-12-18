FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.1
# See https://github.com/OSGeo/gdal/tree/master/docker/ubuntu-small
#   Ubuntu 24.04 LTS
#   Python 3.12.3
#   GDAL 3.11.1

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-gdal \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --break-system-packages uv \
    && python --version \
    && echo "GDAL $(gdalinfo --version)" \
    && uv --version

# Add venv to PATH so python can be called directly.
# Configure uv to avoid some CLI parameters.
# UV_SYSTEM_PYTHON ensures uv uses the Python 3.12.3 from the GDAL base image.
ENV PATH="/root/.local/bin:/marine_litter/.venv/bin:${PATH}" \
    UV_SYSTEM_PYTHON=true \
    UV_PROJECT_ENVIRONMENT=/marine_litter/.venv \
    UV_LINK_MODE=copy \
    UV_LOCKED=true \
    UV_NO_DEV=true

WORKDIR /marine_litter

RUN mkdir -p images/downloaded \
    && mkdir -p images/predicted \
    && mkdir -p secrets \
    && mkdir -p /root/.cache/torch/hub/checkpoints \
    && MODEL_CKPT='epoch=54-val_loss=0.50-auroc=0.987.ckpt' \
    && wget --no-check-certificate "http://dalic.de/mi4people/${MODEL_CKPT}" \
    && mv "${MODEL_CKPT}" /root/.cache/torch/hub/checkpoints/"${MODEL_CKPT}"

# Sync 3rd parties only for Docker cache efficiency
#   Note `--no-install-project`, still uv might need a 'README.md' stub.
COPY ../pyproject.toml .
COPY ../uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv \
    echo "# Marine Litter" > README.md \
    && uv venv --python-preference system --system-site-packages \
    && uv sync --no-install-project

# Copy code (changes more frequently), and provide project
COPY ../LICENSE.txt .
COPY ../README.md .
COPY ../resources/ ./resources
COPY ../scripts/ ./scripts
COPY ../src/ ./src
RUN uv sync

# Provide bash (see 'readme.md' for usage)
CMD ["/bin/bash"]
