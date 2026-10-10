from pathlib import Path
from typing import Any

import geopandas as gpd
import pytest
import rasterio
import torch

from marine_litter.landmask import NoWaterError, water_mask
from marine_litter.tif_processing import get_tiff_layout, load_model, predict_litter


# @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
@pytest.mark.parametrize("checkpoint_fixture", ["checkpoint_path", None])
@pytest.mark.parametrize("cuda_or_cpu", ["cuda", "cpu"])
def test_run_prediction_on_file(
    combined_tif_from_up42_zip: Path, checkpoint_fixture: str, request: pytest.FixtureRequest, cuda_or_cpu: str
) -> None:
    info: dict[str, Any] = get_tiff_layout(combined_tif_from_up42_zip)
    assert info["block_size"] == (1176, 1)
    assert info["raster_size"] == (1176, 1176)
    assert info["image_structure"] == {"INTERLEAVE": "PIXEL"}
    assert info["is_scanline"] is True
    assert info["is_striped"] is False
    assert info["is_tiled"] is False

    checkpoint_path = request.getfixturevalue(checkpoint_fixture) if checkpoint_fixture else None
    if checkpoint_path:
        assert checkpoint_path.is_file()

    if cuda_or_cpu == "cuda" and (torch.cuda.device_count() == 0 or not torch.cuda.is_available()):
        pytest.skip("No CUDA devices found, skipping CUDA test")

    model = load_model(cuda_or_cpu, checkpoint_path)
    result_tif = predict_litter(combined_tif_from_up42_zip, model, cuda_or_cpu)

    assert result_tif
    info = get_tiff_layout(result_tif)
    assert info["block_size"] == (256, 256)
    assert info["raster_size"] == (1176, 1176)
    assert info["image_structure"]["LAYOUT"] == "COG"
    assert info["is_scanline"] is False
    assert info["is_striped"] is False
    assert info["is_tiled"] is True


def test_run_prediction_logs(caplog):
    model = load_model("cuda", Path("nonexistent.ckpt"))
    assert "does not exist -> use default weights" in caplog.text

    result = predict_litter(Path("nonexistent.tif"), model, "cuda")
    assert result is None
    assert "Error processing" in caplog.text


def test_predict_with_land_mask(combined_tif_copy: Path, sea_areas_with_island: gpd.GeoDataFrame) -> None:
    model = load_model("cpu", None)
    result_tif = predict_litter(combined_tif_copy, model, "cpu", sea_areas_with_island, 0)

    assert result_tif
    water = water_mask(combined_tif_copy, sea_areas_with_island, 0)
    with rasterio.open(result_tif) as src:
        prediction = src.read(1)
    assert (prediction[~water] == 0).all()


def test_predict_skips_tile_without_water(combined_tif_copy: Path, sea_areas: gpd.GeoDataFrame) -> None:
    atlantic = gpd.GeoDataFrame(geometry=sea_areas.translate(xoff=-30))
    with pytest.raises(NoWaterError):
        predict_litter(combined_tif_copy, torch.nn.Identity(), "cpu", atlantic, 250)
    assert not list(combined_tif_copy.parent.glob("*_prediction.tif"))
