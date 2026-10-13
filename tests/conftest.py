import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from marine_litter.ml_settings import MLSettings


@pytest.fixture(scope="session")
def an_up42_zip(testdata_root: Path) -> Path:
    return testdata_root / "up42_ordered_example_01.zip"


@pytest.fixture(scope="session")
def checkpoint_path(env_file: Path) -> Path:
    settings = MLSettings(env_file=env_file)
    return settings.checkpoints / settings.checkpoint_file


@pytest.fixture(scope="session")
def combined_tif_from_up42_zip(testdata_root: Path) -> Generator[Path, None, None]:
    """:returns: a GeoTIFF, like needed as input for `marinedebrisdetector.predictor.ScenePredictor`"""
    combined_tif_zip = testdata_root / "up42_ordered_example_01_combined.tif.zip"
    combined_tif = combined_tif_zip.stem
    with TemporaryDirectory(prefix=f"{__name__}_") as d:
        with zipfile.ZipFile(combined_tif_zip, "r") as zip_ref:
            extracted = Path(zip_ref.extract(combined_tif, path=d))
            yield extracted


@pytest.fixture(scope="session")
def env_file(project_root: Path) -> Path:
    return project_root / ".example.env"


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def testdata_root(project_root: Path) -> Path:
    return project_root / "testdata"
