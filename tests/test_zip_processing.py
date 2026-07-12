import shutil
import zipfile
from pathlib import Path
from typing import Any

import pytest

from marine_litter.tif_processing import get_tiff_layout
from marine_litter.zip_processing import process_zip


def test_process_zip(tmp_path: Path, an_up42_zip: Path) -> None:
    test_zip = tmp_path / "test.zip"
    shutil.copy(an_up42_zip, test_zip)

    combined_tif = process_zip(test_zip)

    assert combined_tif.exists()
    assert combined_tif.suffix == ".tif"
    assert combined_tif.stat().st_size > 0
    assert not (tmp_path / test_zip.stem).exists(), "Extract dir should be cleaned up"
    assert not any(f.suffix == ".vrt" for f in tmp_path.glob("*")), "VRT should be cleaned up"

    info: dict[str, Any] = get_tiff_layout(combined_tif)
    assert info["block_size"] == (1176, 1)
    assert info["raster_size"] == (1176, 1176)
    assert info["image_structure"] == {"INTERLEAVE": "PIXEL"}
    assert info["is_scanline"] is True
    assert info["is_striped"] is False
    assert info["is_tiled"] is False


def test_process_zip_error_no_tif_files(tmp_path: Path) -> None:
    test_zip = tmp_path / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("metadata.xml", "<root></root>")
        zf.writestr("other_file.txt", "content")

    with pytest.raises(ValueError, match="No .tif files starting with 'B' found"):
        process_zip(test_zip)


def test_process_zip_error_no_metadata(tmp_path: Path) -> None:
    test_zip = tmp_path / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("B01.tif", b"\x00" * 100)

    with pytest.raises(FileNotFoundError, match="'metadata.xml' not found in zip"):
        process_zip(test_zip)


def test_process_zip_error_tile_id(tmp_path: Path) -> None:
    test_zip = tmp_path / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("B01.tif", b"\x00" * 100)
        zf.writestr("metadata.xml", "<root><OTHER_TAG>value</OTHER_TAG></root>")

    with pytest.raises(ValueError, match="TILE_ID not found in 'metadata.xml'"):
        process_zip(test_zip)
