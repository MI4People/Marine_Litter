#!/usr/bin/env python3
import glob, os
from osgeo import gdal

# ───────── PARAMETERS ─────────────────────────────────────────────────────────
INPUT_PATTERN = "examples_for_merging/*prediction.tif" # that's where I put my samples
TARGET_SRS    = "EPSG:4326" # standard parameter but can be changed
PIXEL_SIZE    = 0.0000898315
VRT_FILENAME  = "mosaic.vrt"
OUTPUT_TIF    = "mosaic.tif"
REPROJ_COPTS  = ["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=YES"]
FINAL_COPTS   = ["TILED=YES", "COMPRESS=DEFLATE",
                 "PREDICTOR=2", "BIGTIFF=YES", "COPY_SRC_OVERVIEWS=YES"]

# 1) Reproject & resample each tile
os.makedirs("reproj", exist_ok=True)
reproj_files = []
for src in glob.glob(INPUT_PATTERN):
    dst = os.path.join("reproj", os.path.basename(src))
    print(f"Reprojecting {src} → {dst}")
    gdal.Warp(
        dst, src,
        format="GTiff",
        dstSRS=TARGET_SRS,
        xRes=PIXEL_SIZE, yRes=PIXEL_SIZE,
        resampleAlg="bilinear",
        creationOptions=REPROJ_COPTS
    )
    reproj_files.append(dst)

# 2) Build the VRT (now with explicit xRes/yRes + tap)
print(f"Building VRT: {VRT_FILENAME}")
vrt_opts = gdal.BuildVRTOptions(
    xRes                 = PIXEL_SIZE,      # required for targetAlignedPixels
    yRes                 = PIXEL_SIZE,
    resampleAlg          = "bilinear",      
    targetAlignedPixels  = True,            
    addAlpha             = True,            
    VRTNodata            = "0 0 0"         
)
gdal.BuildVRT(VRT_FILENAME, reproj_files, options=vrt_opts)

# 3) Translate VRT to the final GeoTIFF
print(f"Translating VRT → {OUTPUT_TIF}")
gdal.Translate(
    OUTPUT_TIF, VRT_FILENAME,
    creationOptions=FINAL_COPTS
)

print("Done! Your seamless mosaic is:", OUTPUT_TIF)
