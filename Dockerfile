# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory to /marine_litter
WORKDIR /marine_litter

# Install system dependencies (e.g., GDAL, etc.)
RUN apt-get update && apt-get install -y \
    wget \ 
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN export CPLUS_INCLUDE_PATH=/usr/include/gdal
RUN export C_INCLUDE_PATH=/usr/include/gdal

RUN pip install --global-option=build_ext --global-option="-I/usr/include/gdal" GDAL==`gdal-config --version`

# Copy the current directory contents into the container at /marine_litter
COPY . /marine_litter

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables for the UP42 credentials and config path

RUN mkdir -p images/downloaded
RUN mkdir -p images/predicted
RUN mkdir -p secrets
RUN mkdir -p /root/.cache/torch/hub/checkpoints
RUN wget --no-check-certificate 'http://dalic.de/mi4people/epoch=54-val_loss=0.50-auroc=0.987.ckpt'
RUN mv epoch=54-val_loss=0.50-auroc=0.987.ckpt /root/.cache/torch/hub/checkpoints/epoch=54-val_loss=0.50-auroc=0.987.ckpt

ENV DAYBEFORE=2
ENV PREDICTE_WORKERS=1
ENV ORDER_WORKERS=10
ENV DEVICE="cpu"

# Default command to run the download script
CMD ["python", "src/main.py", "&&", "exit"]
