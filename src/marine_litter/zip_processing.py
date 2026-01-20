import logging
import shutil
import zipfile
from pathlib import Path

from osgeo import gdal

log = logging.getLogger(__name__)


def process_zip(zip_path: Path) -> Path:
    """Process a ZIP file containing satellite imagery bands and metadata.
    Returns a scanline GeoTIFF for efficient sequential processing by the predictor.
    """
    extract_dir = zip_path.parent / zip_path.stem
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    tif_files = sorted(extract_dir.glob("B*.tif"))  # the relevant images to combine
    if not tif_files:
        raise ValueError(f"No .tif files starting with 'B' found in '{zip_path.name}'.")

    log.info(f"Found {len(tif_files)} 'B*.tif' files in '{zip_path.name}'.")

    metadata_file = extract_dir / "metadata.xml"
    if not metadata_file.exists():
        raise FileNotFoundError(f"'{metadata_file.name}' not found in zip!")

    metadata_content = metadata_file.read_text(encoding="utf-8")
    start_tag = '<TILE_ID metadataLevel="Brief">'
    end_tag = "</TILE_ID>"
    start_index = metadata_content.find(start_tag) + len(start_tag)
    end_index = metadata_content.find(end_tag, start_index)
    if start_index == -1 or end_index == -1:
        raise ValueError(f"Tag TILE_ID not found in '{metadata_file.name}'")

    # merge bands into one file
    tile_id = metadata_content[start_index:end_index].strip()
    vrt_filename = zip_path.parent / f"{tile_id}.vrt"
    vrt_options = gdal.BuildVRTOptions(separate=True, srcNodata=0, VRTNodata=0)
    gdal.BuildVRT(str(vrt_filename), [str(f) for f in tif_files], options=vrt_options)

    # final data handling
    combined_tif = vrt_filename.with_suffix(".tif")
    gdal.Translate(
        str(combined_tif),  # to
        str(vrt_filename),  # from
        format="GTiff",  # https://gdal.org/en/stable/drivers/raster/gtiff.html
        scaleParams=[[0, 10000, 0, 255]],  # map brightness
        outputType=gdal.GDT_Byte,
        noData=0,
    )

    # clean up
    vrt_filename.unlink()
    shutil.rmtree(extract_dir, ignore_errors=True)

    return combined_tif
