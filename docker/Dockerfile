FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4
# This base image (https://github.com/OSGeo/gdal/tree/master/docker/) comes with
#   Ubuntu 24.04 LTS
#   Python 3.12.3
#   GDAL 3.11.4
#
# See parallel 'readme.md' for usage.

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/* \
    && python -c "from osgeo import gdal; print(f'Python gdal: {gdal.__version__}')" || exit 1

# Add venv to PATH so python can be called directly, and
# configure uv to avoid some CLI parameters (https://docs.astral.sh/uv/reference/cli/).
ENV PATH="/root/.local/bin:/marine_litter/.venv/bin:${PATH}" \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /marine_litter

# Optional: provide SHA256 at build time for supply-chain integrity verification.
# Usage: docker build --build-arg MODEL_CKPT_SHA256=<hash> ...
# To compute the hash: sha256sum 'epoch=54-val_loss=0.50-auroc=0.987.ckpt'
ARG MODEL_CKPT_SHA256=""

RUN mkdir -p images/downloaded \
    && mkdir -p images/predicted \
    && mkdir -p secrets \
    && mkdir -p /root/.cache/torch/hub/checkpoints \
    && MODEL_CKPT='epoch=54-val_loss=0.50-auroc=0.987.ckpt' \
    && wget "https://dalic.de/mi4people/${MODEL_CKPT}" \
    && if [ -n "${MODEL_CKPT_SHA256}" ]; then \
         echo "${MODEL_CKPT_SHA256}  ${MODEL_CKPT}" | sha256sum -c - ; \
       fi \
    && mv "${MODEL_CKPT}" /root/.cache/torch/hub/checkpoints/"${MODEL_CKPT}"

# NOTE, especially torch and cuda dependencies are huge, so we need to
# - use layering (to save `docker build` time)
# - keep the cache outside the Docker image (to save download time and image size)
# Dependencies (change less frequently)
COPY ../pyproject.toml .
COPY ../uv.lock .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv --system-site-packages .venv \
    && uv sync --frozen --no-install-project

# Copy code (changes more frequently), and provide project
COPY ../LICENSE.txt .
COPY ../README.md .
COPY ../resources/ ./resources
COPY ../scripts/ ./scripts
COPY ../src/ ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

CMD ["/bin/bash"]
