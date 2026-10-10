import argparse
import logging
from pathlib import Path
from time import perf_counter
from typing import Any

import geopandas as gpd
import torch
from marinedebrisdetector.predictor import ScenePredictor
from osgeo import gdal
from osgeo.gdal import Dataset

from marine_litter.landmask import NoWaterError, fill_land, water_mask, zero_land

gdal.UseExceptions()

log = logging.getLogger(__name__)


def load_model(cpu_or_cuda: str, checkpoint_path: Path | None) -> torch.nn.Module:
    """Load the marinedebrisdetector model once, for reuse across multiple `predict_litter()` calls.
    If checkpoint_path is provided and exists, load custom weights, otherwise hub default ones.
    """
    if checkpoint_path and not checkpoint_path.is_file():
        log.warning(f"'{checkpoint_path.name}' does not exist -> use default weights")
        checkpoint_path = None

    model = torch.hub.load("MarcCoru/marinedebrisdetector", "unetpp", verbose=True)
    if checkpoint_path:
        torch.serialization.add_safe_globals([argparse.Namespace])  # needed for `weights_only`
        state = torch.load(checkpoint_path, weights_only=True, map_location=cpu_or_cuda)
        # Lightning checkpoints store weights under 'state_dict' key
        if isinstance(state, dict) and "state_dict" in state:
            model.load_state_dict(state["state_dict"])
            log.info(f"Loaded custom checkpoint: {checkpoint_path.name}")
    return model


def predict_litter(
    tif_file: Path,
    model: torch.nn.Module,
    cpu_or_cuda: str,
    sea_areas: gpd.GeoDataFrame | None = None,
    buffer_m: float = 0,
) -> Path | None:
    """Run marine litter prediction on a single file using a pre-loaded marinedebrisdetector model.
    Load `model` once per batch with `load_model()` and reuse it across calls, rather than reloading it per file.

    With `sea_areas` (see `landmask.load_sea_areas()`), land is masked in `tif_file` (in place) before prediction,
    and set to 0 in the prediction, see 'specs/landmask.md'.

    For GeoTIFF/COG format references see:
    - https://en.wikipedia.org/wiki/GeoTIFF
    - https://www.ogc.org/announcement/cloud-optimized-geotiff-cog-published-as-official-ogc-standard/
    - https://gdal.org/en/stable/drivers/raster/cog.html
    - https://element84.com/software-engineering/remote-sensing/cloud-optimized-geotiff-vs-the-meta-raster-format

    :returns: output filename if successful, else `None`.
    :raises NoWaterError: if `tif_file` has no water pixel, it is skipped then.
    """
    log.info(f"Predict '{tif_file.name}' using {cpu_or_cuda.upper()}")
    temp_predicted = tif_file.parent / f"{tif_file.stem}_temp_predicted.tif"
    try:
        water = None
        if sea_areas is not None:
            t_start = perf_counter()
            water = water_mask(tif_file, sea_areas, buffer_m)
            n_water = fill_land(tif_file, water) if water.any() else 0
            log.info(f"  Land masking: {water.mean():.1%} water, {perf_counter() - t_start:.2f} seconds")
            if n_water == 0:
                log.info(f"  '{tif_file.name}': skipped, no water")
                raise NoWaterError(tif_file.name)

        scene_predictor = ScenePredictor(device=cpu_or_cuda)
        t_start = perf_counter()
        scene_predictor.predict(model, str(tif_file), str(temp_predicted))
        t_end = perf_counter()
        log.info(f"  Prediction time: {t_end - t_start:.2f} seconds")
        if water is not None:
            zero_land(temp_predicted, water)

        result_cog_tif = tif_file.parent / f"{tif_file.stem}_prediction.tif"
        translated = gdal.Translate(
            str(result_cog_tif),
            str(temp_predicted),
            options=gdal.TranslateOptions(format="COG", creationOptions=["BLOCKSIZE=256", "COMPRESS=DEFLATE"]),
        )
        if translated is None:
            raise RuntimeError(f"gdal.Translate produced no dataset for '{result_cog_tif.name}'")

        log.info(f"  '{tif_file.name}': success")
        return result_cog_tif

    except NoWaterError:
        raise
    except Exception:
        log.exception(f"Error processing {tif_file}")
        return None
    finally:
        temp_predicted.unlink(missing_ok=True)  # remove temporary file, even on failure


def get_tiff_layout(tiff: Path) -> dict[str, Any]:
    ds: Dataset = gdal.Open(str(tiff))
    if ds is None:
        raise FileNotFoundError(f"gdal could not open '{tiff}' as a raster dataset")
    band = ds.GetRasterBand(1)
    bx, by = band.GetBlockSize()
    rx, ry = ds.RasterXSize, ds.RasterYSize
    image_structure = ds.GetMetadata("IMAGE_STRUCTURE") or {}
    is_tiled = image_structure.get("TILED", "").upper() == "YES" or (bx < rx and by < ry)
    is_striped = not is_tiled and bx == rx and 1 < by < ry
    is_scanline = not is_tiled and bx == rx and by == 1

    return {
        "block_size": (bx, by),
        "raster_size": (rx, ry),
        "image_structure": image_structure,
        "is_scanline": is_scanline,
        "is_striped": is_striped,
        "is_tiled": is_tiled,
    }
