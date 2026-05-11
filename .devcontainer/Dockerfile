FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG USERNAME=ubuntu
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update \
    && apt-get install -y sudo python3-venv \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*
