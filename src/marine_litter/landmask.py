"""Mask land in satellite tiles, so that marine litter is only detected on water, see 'specs/landmask.md'.

Water is defined by the IHO Sea Areas of Marine Regions (https://www.marineregions.org), fetched via WFS.
"""

import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.io import DatasetWriter
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from shapely.geometry import box

log = logging.getLogger(__name__)

WFS_URL = "https://geo.vliz.be/geoserver/MarineRegions/wfs"
WFS_LAYER = "MarineRegions:iho"
WFS_TIMEOUT_S = 60
AOI_MARGIN_DEG = 1.0  # covers Sentinel-2 tiles (~110 km) overlapping the AOI edge
BLOCK_ROWS = 512  # rows per block when reading/writing tiles, keeps memory bounded


class NoWaterError(Exception):
    """Raised for a tile without any water pixel, which is skipped then."""


def load_sea_areas(aoi_path: Path, cache_path: Path) -> gpd.GeoDataFrame | None:
    """Get the IHO sea areas around the AOI from the Marine Regions WFS, and store them in `cache_path`.
    If the web is not available, fall back to `cache_path`.
    :returns: sea areas in EPSG:4326, or `None` if neither the web nor the local copy is available.
    """
    try:
        minx, miny, maxx, maxy = gpd.read_file(aoi_path).to_crs("EPSG:4326").total_bounds
        bbox = (minx - AOI_MARGIN_DEG, miny - AOI_MARGIN_DEG, maxx + AOI_MARGIN_DEG, maxy + AOI_MARGIN_DEG)
        sea_areas = _fetch_sea_areas(bbox)
    except Exception as e:
        log.warning(f"Could not fetch sea areas from {WFS_URL}: {e}")
    else:
        try:
            _write_atomic(sea_areas, cache_path)
        except Exception as e:
            log.warning(f"Could not store sea areas in '{cache_path}': {e}")
        _log_sea_areas(sea_areas, WFS_URL)
        return sea_areas

    if not cache_path.is_file():
        log.warning(f"No local copy of sea areas in '{cache_path}' -> land masking is off for this run")
        return None
    try:
        sea_areas = gpd.read_file(cache_path).to_crs("EPSG:4326")
    except Exception as e:
        log.warning(f"Could not read sea areas from '{cache_path}' -> land masking is off for this run: {e}")
        return None
    age_days = (time.time() - cache_path.stat().st_mtime) / 86400
    _log_sea_areas(sea_areas, f"local copy '{cache_path}' ({age_days:.1f} days old)")
    return sea_areas


def _fetch_sea_areas(bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": WFS_LAYER,
        "bbox": ",".join(f"{v:.4f}" for v in bbox),
        "outputFormat": "application/json",
    }
    with urllib.request.urlopen(f"{WFS_URL}?{urllib.parse.urlencode(params)}", timeout=WFS_TIMEOUT_S) as response:
        features = json.load(response)["features"]
    sea_areas = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")[["name", "mrgid", "geometry"]]
    # The WFS matches by envelope, so e.g. the antimeridian-spanning North Pacific matches any bbox -> clip.
    sea_areas = gpd.clip(sea_areas, box(*bbox))
    sea_areas = sea_areas[~sea_areas.is_empty]
    if sea_areas.empty:
        raise ValueError(f"no sea areas within bbox {bbox}")
    return sea_areas


def _write_atomic(sea_areas: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    sea_areas.to_file(tmp, driver="GeoJSON")
    tmp.replace(path)


def _log_sea_areas(sea_areas: gpd.GeoDataFrame, source: str) -> None:
    names = ", ".join(f"{name} ({mrgid})" for name, mrgid in zip(sea_areas["name"], sea_areas["mrgid"], strict=True))
    log.info(f"Sea areas from {source}: {names}")


def water_mask(tif: Path, sea_areas: gpd.GeoDataFrame, buffer_m: float) -> np.ndarray:
    """Rasterize the sea areas on the grid of `tif`.
    :param buffer_m: grow the sea areas by this many meters inland, as the IHO coastline is coarse.
    :returns: boolean array of the tile's shape, `True` for water.
    """
    with rasterio.open(tif) as src:
        crs, transform, shape, bounds = src.crs, src.transform, src.shape, src.bounds
    if crs is None or not crs.is_projected:
        raise ValueError(f"'{tif.name}' needs a projected CRS in meters for the buffer, got {crs}")

    # Clip in EPSG:4326 first: cheap, and avoids reprojecting far away or global polygons.
    # The margin must cover the buffer: 1° longitude is >50 km up to latitude 63°.
    margin_deg = 0.01 + buffer_m / 50_000
    footprint = box(*transform_bounds(crs, "EPSG:4326", *bounds, densify_pts=21)).buffer(margin_deg)
    sea = gpd.clip(sea_areas.to_crs("EPSG:4326"), footprint)
    sea = sea[~sea.is_empty]
    if sea.empty:
        return np.zeros(shape, dtype=bool)

    geometries = sea.to_crs(crs).geometry
    if buffer_m:
        geometries = geometries.buffer(buffer_m)
    mask = rasterize(((g, 1) for g in geometries), out_shape=shape, transform=transform, fill=0, dtype=np.uint8)
    return mask.view(np.bool_)


def fill_land(tif: Path, water: np.ndarray) -> int:
    """Fill land pixels of `tif` in place with the per-band median of its water pixels, a water-like neutral value.
    Nodata pixels (0 in all bands) stay untouched and are not used for the median.
    :returns: number of valid water pixels, nothing is changed if 0.
    """
    with rasterio.open(tif, "r+") as dst:
        _check_shape(dst, water)
        dtype = np.dtype(dst.dtypes[0])
        if dtype not in (np.uint8, np.uint16):
            raise ValueError(f"'{tif.name}' must be uint8 or uint16, got {dtype}")
        windows = _row_windows(dst)

        # 1st pass: histograms of the water pixels, for exact medians
        n_bins = 2 ** (8 * dtype.itemsize)
        hist = np.zeros((dst.count, n_bins), dtype=np.int64)
        for w in windows:
            data = dst.read(window=w)
            water_px = data[:, water[_rows(w)] & data.any(axis=0)]
            for band, values in enumerate(water_px):
                hist[band] += np.bincount(values, minlength=n_bins)

        n_water = int(hist[0].sum())
        if n_water == 0:
            return 0
        median = (hist.cumsum(axis=1) >= (n_water + 1) // 2).argmax(axis=1).astype(dtype)
        log.debug(f"  '{tif.name}': fill land with per-band water median {median.tolist()}")

        # 2nd pass: fill
        for w in windows:
            data = dst.read(window=w)
            land = ~water[_rows(w)] & data.any(axis=0)
            if land.any():
                data[:, land] = median[:, np.newaxis]
                dst.write(data, window=w)
    return n_water


def zero_land(tif: Path, water: np.ndarray) -> None:
    """Set all land pixels of `tif` to 0 in place, e.g. in a prediction."""
    with rasterio.open(tif, "r+") as dst:
        _check_shape(dst, water)
        for w in _row_windows(dst):
            land = ~water[_rows(w)]
            if land.any():
                data = dst.read(window=w)
                data[:, land] = 0
                dst.write(data, window=w)


def _check_shape(dst: DatasetWriter, water: np.ndarray) -> None:
    if water.shape != dst.shape:
        raise ValueError(f"Water mask shape {water.shape} does not match '{dst.name}' {dst.shape}")


def _row_windows(dst: DatasetWriter) -> list[Window]:
    return [Window(0, r, dst.width, min(BLOCK_ROWS, dst.height - r)) for r in range(0, dst.height, BLOCK_ROWS)]


def _rows(window: Window) -> slice:
    return slice(window.row_off, window.row_off + window.height)
