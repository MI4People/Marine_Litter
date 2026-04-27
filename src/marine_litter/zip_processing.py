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
        for member in zip_ref.infolist():
            member_path = (extract_dir / member.filename).resolve()
            if not member_path.is_relative_to(extract_dir.resolve()):
                raise ValueError(f"ZipSlip detected: '{member.filename}' escapes target directory")
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
    raw_index = metadata_content.find(start_tag)
    if raw_index == -1:
        raise ValueError(f"Tag TILE_ID not found in '{metadata_file.name}'")
    start_index = raw_index + len(start_tag)
    end_index = metadata_content.find(end_tag, start_index)
    if end_index == -1:
        raise ValueError(f"Closing </TILE_ID> not found in '{metadata_file.name}'")

    # merge bands into one file
    tile_id = metadata_content[start_index:end_index].strip()
    vrt_filename = zip_path.parent / f"{tile_id}.vrt"
    vrt_options = gdal.BuildVRTOptions(separate=True, srcNodata=0, VRTNodata=0)
    # ML-047: Check BuildVRT result and explicitly close dataset to release file handles
    vrt_ds = gdal.BuildVRT(str(vrt_filename), [str(f) for f in tif_files], options=vrt_options)
    if vrt_ds is None:
        raise RuntimeError(f"GDAL BuildVRT failed for '{zip_path.name}'")
    vrt_ds.FlushCache()
    vrt_ds = None  # close dataset before Translate reads it

    # final data handling
    combined_tif = vrt_filename.with_suffix(".tif")
    # ML-047: Check Translate result and explicitly close dataset
    translate_ds = gdal.Translate(
        str(combined_tif),  # to
        str(vrt_filename),  # from
        format="GTiff",  # https://gdal.org/en/stable/drivers/raster/gtiff.html
        scaleParams=[[0, 10000, 0, 255]],  # map brightness
        outputType=gdal.GDT_Byte,
        noData=0,
    )
    if translate_ds is None:
        raise RuntimeError(f"GDAL Translate failed for '{vrt_filename.name}'")
    translate_ds.FlushCache()
    translate_ds = None  # close dataset to release file handles

    # clean up
    vrt_filename.unlink()
    shutil.rmtree(extract_dir, ignore_errors=True)

    return combined_tif
