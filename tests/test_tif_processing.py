import logging
from pathlib import Path

import pytest
import torch

from marine_litter.tif_processing import get_tiff_layout, predict_litter


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
@pytest.mark.parametrize("checkpoint_fixture", ["checkpoint_path", None])
def test_run_prediction_on_file(combined_tif_from_up42_zip, checkpoint_fixture, request):
    info: dict = get_tiff_layout(combined_tif_from_up42_zip)
    assert info["block_size"] == (1176, 1)
    assert info["raster_size"] == (1176, 1176)
    assert info["image_structure"] == {"INTERLEAVE": "PIXEL"}
    assert info["is_scanline"] is True
    assert info["is_striped"] is False
    assert info["is_tiled"] is False

    checkpoint_path = request.getfixturevalue(checkpoint_fixture) if checkpoint_fixture else None
    if checkpoint_path:
        assert checkpoint_path.is_file()

    result_tif = predict_litter(combined_tif_from_up42_zip, "cuda", checkpoint_path)

    assert result_tif
    info: dict = get_tiff_layout(result_tif)
    assert info["block_size"] == (256, 256)
    assert info["raster_size"] == (1176, 1176)
    assert info["image_structure"]["LAYOUT"] == "COG"
    assert info["is_scanline"] is False
    assert info["is_striped"] is False
    assert info["is_tiled"] is True


def test_run_prediction_logs(caplog):
    result = predict_litter(Path("nonexistent.tif"), "cuda", Path("nonexistent.ckpt"))
    assert result is None
    assert "does not exist -> use default weights" in caplog.text
    assert "Error processing" in caplog.text


def test_predict_litter_log_message_shows_uppercased_device(caplog):
    """ML-009: Verify log shows 'CUDA' or 'CPU', not the method object repr."""
    with caplog.at_level(logging.INFO):
        predict_litter(Path("nonexistent.tif"), "cuda", None)
    assert "using CUDA" in caplog.text
    assert "built-in method upper" not in caplog.text


def test_predict_litter_log_message_cpu(caplog):
    """ML-009: Verify log shows 'CPU' when device is cpu."""
    with caplog.at_level(logging.INFO):
        predict_litter(Path("nonexistent.tif"), "cpu", None)
    assert "using CPU" in caplog.text


def test_get_tiff_layout_nonexistent_file():
    """ML-047: gdal.Open returns None for nonexistent files — must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="GDAL could not open"):
        get_tiff_layout(Path("this_file_does_not_exist.tif"))
