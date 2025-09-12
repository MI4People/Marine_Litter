FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.1
# See https://github.com/OSGeo/gdal/tree/master/docker/ubuntu-small
#   Ubuntu 24.04 LTS
#   Python 3.12.3
#   GDAL 3.11.1
#   PyTorch via pyproject.toml

RUN apt-get update && apt-get install -y \
    pipx \
    python3-gdal \
    wget \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:${PATH}"
RUN pipx install uv ruff \
    && python3 --version \
    && echo "GDAL $(gdalinfo --version)" \
    && uv --version \
    && ruff --version

WORKDIR /marine_litter

RUN mkdir -p images/downloaded \
    && mkdir -p images/predicted \
    && mkdir -p secrets \
    && mkdir -p /root/.cache/torch/hub/checkpoints \
    && MODEL_CKPT='epoch=54-val_loss=0.50-auroc=0.987.ckpt' \
    && wget --no-check-certificate "http://dalic.de/mi4people/${MODEL_CKPT}" \
    && mv "${MODEL_CKPT}" /root/.cache/torch/hub/checkpoints/"${MODEL_CKPT}"

COPY ../resources/ ./resources
COPY ../scripts/ ./scripts
COPY ../src/ ./src
COPY ../.example.env .
COPY ../pyproject.toml .
COPY ../README.md .
COPY ../uv.lock .

uv sync --locked --no-install-project --no-dev
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=./src
ENV PYTHONUNBUFFERED=1

# ENV DAYS_BEFORE=2
# ENV ORDER_WORKERS=8
# ENV PREDICT_WORKERS=4
# ENV DEVICE=cuda
CMD ["bash", "-c", "export PS1='\\w\\$ '; exec bash --login -i"]
