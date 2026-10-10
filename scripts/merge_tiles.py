#!/usr/bin/env python3
import glob
import logging
import os
from pathlib import Path

from osgeo import gdal

log = logging.getLogger(__name__)


# ───────── PARAMETERS ─────────────────────────────────────────────────────────
INPUT_PATTERN = "examples_for_merging/*prediction.tif"  # that's where I put my samples
TARGET_SRS = "EPSG:4326"  # standard parameter but can be changed
PIXEL_SIZE = 0.0000898315
VRT_FILENAME = "mosaic.vrt"
OUTPUT_TIF = "mosaic.tif"
REPROJ_COPTS = ["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=YES"]
FINAL_COPTS = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "BIGTIFF=YES", "COPY_SRC_OVERVIEWS=YES"]


def main(  # noqa: PLR0913, PLR0917
    input_pattern: str = INPUT_PATTERN,
    target_srs: str = TARGET_SRS,
    pixel_size: float = PIXEL_SIZE,
    vrt_filename: str = VRT_FILENAME,
    output_tif: str = OUTPUT_TIF,
    reproj_copts: list[str] | None = None,
    final_copts: list[str] | None = None,
) -> None:
    if reproj_copts is None:
        reproj_copts = REPROJ_COPTS
    if final_copts is None:
        final_copts = FINAL_COPTS

    # 1) Reproject & resample each tile
    os.makedirs("reproj", exist_ok=True)
    reproj_files = []
    for src in glob.glob(input_pattern):
        dst = os.path.join("reproj", os.path.basename(src))
        log.info(f"Reprojecting {src} → {dst}")
        gdal.Warp(
            dst,
            src,
            format="GTiff",
            dstSRS=target_srs,
            xRes=pixel_size,
            yRes=pixel_size,
            resampleAlg="bilinear",
            creationOptions=reproj_copts,
        )
        reproj_files.append(dst)

    # 2) Build the VRT (now with explicit xRes/yRes + tap)
    log.info(f"Building VRT: {vrt_filename}")
    vrt_opts = gdal.BuildVRTOptions(
        xRes=pixel_size,  # required for targetAlignedPixels
        yRes=pixel_size,
        resampleAlg="bilinear",
        targetAlignedPixels=True,
        addAlpha=True,
        VRTNodata="0 0 0",
    )
    gdal.BuildVRT(vrt_filename, reproj_files, options=vrt_opts)

    # 3) Translate VRT to the final GeoTIFF
    log.info(f"Translating VRT → {output_tif}")
    gdal.Translate(output_tif, vrt_filename, creationOptions=final_copts)
    log.info(f"Done! Your seamless mosaic is: {output_tif}")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])
    main()
