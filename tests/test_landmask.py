import io
import json
import logging
import urllib.error
from pathlib import Path
from typing import Callable

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from marine_litter import landmask
from marine_litter.landmask import fill_land, load_sea_areas, water_mask, zero_land


def _write_tif(path: Path, data: np.ndarray, crs: str = "EPSG:32634") -> Path:
    bands, height, width = data.shape
    transform = from_origin(199980.0, 4700040.0, 10, 10)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        count=bands,
        height=height,
        width=width,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)
    return path


def _read(tif: Path) -> np.ndarray:
    with rasterio.open(tif) as src:
        return src.read()


# ---------- water_mask


def test_water_mask(combined_tif_copy: Path, sea_areas: gpd.GeoDataFrame):
    water = water_mask(combined_tif_copy, sea_areas, 0)
    assert water.shape == (1176, 1176)
    assert water.dtype == bool
    assert 0 < water.mean() < 1


def test_water_mask_buffer_grows_water(combined_tif_copy: Path, sea_areas: gpd.GeoDataFrame):
    assert water_mask(combined_tif_copy, sea_areas, 1000).sum() > water_mask(combined_tif_copy, sea_areas, 0).sum()


def test_water_mask_far_away_sea_is_all_land(combined_tif_copy: Path, sea_areas: gpd.GeoDataFrame):
    atlantic = sea_areas.translate(xoff=-30)
    assert not water_mask(combined_tif_copy, gpd.GeoDataFrame(geometry=atlantic), 250).any()


def test_water_mask_rejects_geographic_crs(tmp_path: Path, sea_areas: gpd.GeoDataFrame):
    tif = _write_tif(tmp_path / "geographic.tif", np.ones((1, 4, 4), dtype=np.uint8), crs="EPSG:4326")
    with pytest.raises(ValueError, match="projected CRS"):
        water_mask(tif, sea_areas, 250)


# ---------- fill_land


def test_fill_land(combined_tif_copy: Path, sea_areas_with_island: gpd.GeoDataFrame):
    water = water_mask(combined_tif_copy, sea_areas_with_island, 0)
    before = _read(combined_tif_copy)
    valid = before.any(axis=0)
    land = valid & ~water
    assert land.sum() > 1000, "test needs valid land pixels"

    n_water = fill_land(combined_tif_copy, water)

    water_px = before[:, valid & water]
    assert n_water == water_px.shape[1]
    lower_median = np.sort(water_px, axis=1)[:, (n_water + 1) // 2 - 1]
    after = _read(combined_tif_copy)
    assert (after[:, land] == lower_median[:, np.newaxis]).all()
    assert (after[:, ~land] == before[:, ~land]).all(), "water and nodata pixels must stay unchanged"


def test_fill_land_uint16(tmp_path: Path):
    data = np.zeros((2, 2, 4), dtype=np.uint16)
    data[0, :, :2] = [[1000, 3000], [2000, 9000]]  # water: left half, band 0
    data[1, :, :2] = 500  # water: left half, band 1
    data[:, 0, 2] = 60000  # land, last column stays nodata
    data[:, 1, 2] = 7
    tif = _write_tif(tmp_path / "uint16.tif", data)
    water = np.zeros((2, 4), dtype=bool)
    water[:, :2] = True

    assert fill_land(tif, water) == 4

    expected = data.copy()
    expected[0, :, 2] = 2000
    expected[1, :, 2] = 500
    assert (_read(tif) == expected).all()


def test_fill_land_without_water(combined_tif_copy: Path):
    before = _read(combined_tif_copy)
    assert fill_land(combined_tif_copy, np.zeros((1176, 1176), dtype=bool)) == 0
    assert (_read(combined_tif_copy) == before).all()


def test_fill_land_rejects_float(tmp_path: Path):
    tif = _write_tif(tmp_path / "float.tif", np.ones((1, 4, 4), dtype=np.float32))
    with pytest.raises(ValueError, match="uint8 or uint16"):
        fill_land(tif, np.ones((4, 4), dtype=bool))


def test_fill_land_rejects_shape_mismatch(tmp_path: Path):
    tif = _write_tif(tmp_path / "small.tif", np.ones((1, 4, 4), dtype=np.uint8))
    with pytest.raises(ValueError, match="does not match"):
        fill_land(tif, np.ones((5, 4), dtype=bool))


# ---------- zero_land


def test_zero_land(tmp_path: Path):
    tif = _write_tif(tmp_path / "prediction.tif", np.full((1, 3, 4), 200, dtype=np.uint8))
    water = np.zeros((3, 4), dtype=bool)
    water[:, :2] = True

    zero_land(tif, water)

    result = _read(tif)[0]
    assert (result[water] == 200).all()
    assert (result[~water] == 0).all()


# ---------- load_sea_areas


@pytest.fixture
def aoi_path(project_root: Path) -> Path:
    return project_root / "resources" / "features.geojson"


@pytest.fixture
def wfs_response(sea_areas: gpd.GeoDataFrame) -> bytes:
    """:returns: WFS-like response with `sea_areas` and a far away area, like the WFS matching the North Pacific."""
    features = json.loads(sea_areas.to_json())["features"]
    pacific = {
        "type": "Feature",
        "geometry": mapping(box(-170, 10, -120, 50)),
        "properties": {"name": "North Pacific Ocean", "mrgid": 1908},
    }
    return json.dumps({"type": "FeatureCollection", "features": [*features, pacific]}).encode()


def _urlopen_returning(payload: bytes) -> Callable[..., io.BytesIO]:
    return lambda url, timeout: io.BytesIO(payload)  # noqa: ARG005


def _urlopen_failing(url: str, timeout: float) -> io.BytesIO:  # noqa: ARG001
    raise urllib.error.URLError("no network")


def test_load_sea_areas_from_web(tmp_path: Path, aoi_path: Path, wfs_response: bytes, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(landmask.urllib.request, "urlopen", _urlopen_returning(wfs_response))
    cache = tmp_path / "sub" / "landmask.geojson"

    sea_areas = load_sea_areas(aoi_path, cache)

    assert sea_areas is not None
    assert sea_areas["mrgid"].tolist() == [3314], "far away sea areas must be clipped away"
    assert gpd.read_file(cache)["mrgid"].tolist() == [3314]
    assert list(cache.parent.iterdir()) == [cache], "no temporary file must be left"


def test_load_sea_areas_falls_back_to_local_copy(
    tmp_path: Path,
    aoi_path: Path,
    sea_areas: gpd.GeoDataFrame,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setattr(landmask.urllib.request, "urlopen", _urlopen_failing)
    cache = tmp_path / "landmask.geojson"
    sea_areas.to_file(cache, driver="GeoJSON")

    with caplog.at_level(logging.INFO):
        result = load_sea_areas(aoi_path, cache)

    assert result is not None
    assert result["mrgid"].tolist() == [3314]
    assert "Could not fetch sea areas" in caplog.text
    assert "local copy" in caplog.text


def test_load_sea_areas_without_web_and_local_copy(
    tmp_path: Path, aoi_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    monkeypatch.setattr(landmask.urllib.request, "urlopen", _urlopen_failing)
    assert load_sea_areas(aoi_path, tmp_path / "landmask.geojson") is None
    assert "land masking is off" in caplog.text


@pytest.mark.parametrize(
    "payload", [b"<html>Service unavailable</html>", b'{"type": "FeatureCollection", "features": []}']
)
def test_load_sea_areas_invalid_response_keeps_local_copy(
    tmp_path: Path, aoi_path: Path, sea_areas: gpd.GeoDataFrame, monkeypatch: pytest.MonkeyPatch, payload: bytes
):
    monkeypatch.setattr(landmask.urllib.request, "urlopen", _urlopen_returning(payload))
    cache = tmp_path / "landmask.geojson"
    sea_areas.to_file(cache, driver="GeoJSON")
    cached = cache.read_bytes()

    result = load_sea_areas(aoi_path, cache)

    assert result is not None
    assert result["mrgid"].tolist() == [3314]
    assert cache.read_bytes() == cached


def test_fetch_sea_areas_live():
    try:
        sea_areas = landmask._fetch_sea_areas((17.0, 41.0, 19.0, 43.0))
    except (urllib.error.URLError, TimeoutError) as e:
        pytest.skip(f"Marine Regions WFS not reachable: {e}")
    assert 3314 in sea_areas["mrgid"].tolist()
    assert 1908 not in sea_areas["mrgid"].tolist()
