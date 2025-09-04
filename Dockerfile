FROM python:3.13-slim

WORKDIR /marine_litter

RUN apt-get update \
    && apt-get install -y \
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

# Copy current directory into the container
COPY . /marine_litter

RUN pip install --no-cache-dir -r requirements.txt
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

# Default command to run
CMD ["python", "src/main.py", "&&", "exit"]
