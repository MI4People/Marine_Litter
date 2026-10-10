FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.5

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ARG USERNAME=ubuntu
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# The libgl1..libxrender1 packages are the X11 and OpenGL libraries that the Qt "xcb" platform
# plugin of `opencv-python` links against, needed by 'scripts/vizualize_tile.py' to open a window.
RUN apt-get update \
    && apt-get install -y sudo python3-venv nano \
        libgl1 libglib2.0-0 libsm6 libxcb1 libxext6 libxkbcommon-x11-0 libxrender1 \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chown root:root /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*
