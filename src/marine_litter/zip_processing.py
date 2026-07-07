import logging
import shutil
import zipfile
from pathlib import Path

from osgeo import gdal

gdal.UseExceptions()

log = logging.getLogger(__name__)


def _safe_extractall(zip_ref: zipfile.ZipFile, dest_dir: Path) -> None:
    """Extract all members of `zip_ref` into `dest_dir`, rejecting entries that would escape it
    (a.k.a. "Zip Slip"), e.g. via absolute paths or '../' components in member names.
    """
    dest_dir = dest_dir.resolve()
    for member in zip_ref.infolist():
        member_path = (dest_dir / member.filename).resolve()
        if not member_path.is_relative_to(dest_dir):
            raise ValueError(f"Unsafe path in zip archive, escapes extraction directory: '{member.filename}'")
    zip_ref.extractall(dest_dir)


def process_zip(zip_path: Path) -> Path:
    """Process a ZIP file containing satellite imagery bands and metadata.
    Returns a scanline GeoTIFF for efficient sequential processing by the predictor.
    """
    extract_dir = zip_path.parent / zip_path.stem
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            _safe_extractall(zip_ref, extract_dir)

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
        start_tag_index = metadata_content.find(start_tag)
        end_index = metadata_content.find(end_tag, start_tag_index + len(start_tag)) if start_tag_index != -1 else -1
        if start_tag_index == -1 or end_index == -1:
            raise ValueError(f"Tag TILE_ID not found in '{metadata_file.name}'")
        start_index = start_tag_index + len(start_tag)

        # merge bands into one file
        tile_id = metadata_content[start_index:end_index].strip()
        vrt_filename = zip_path.parent / f"{tile_id}.vrt"
        vrt_options = gdal.BuildVRTOptions(separate=True, srcNodata=0, VRTNodata=0)
        vrt_dataset = gdal.BuildVRT(str(vrt_filename), [str(f) for f in tif_files], options=vrt_options)
        if vrt_dataset is None:
            raise RuntimeError(f"gdal.BuildVRT produced no dataset for '{vrt_filename.name}'")
        vrt_dataset = None  # flush/close before reading it back below

        # final data handling
        combined_tif = vrt_filename.with_suffix(".tif")
        translated = gdal.Translate(
            str(combined_tif),  # to
            str(vrt_filename),  # from
            format="GTiff",  # https://gdal.org/en/stable/drivers/raster/gtiff.html
            scaleParams=[[0, 10000, 0, 255]],  # map brightness
            outputType=gdal.GDT_Byte,
            noData=0,
        )
        if translated is None:
            raise RuntimeError(f"gdal.Translate produced no dataset for '{combined_tif.name}'")

        vrt_filename.unlink()  # clean up

        return combined_tif
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)
