import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import geopandas as gpd
import pytest
from shapely.geometry import box

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


@pytest.fixture
def combined_tif_copy(combined_tif_from_up42_zip: Path, tmp_path: Path) -> Path:
    """:returns: a copy of `combined_tif_from_up42_zip`, for tests modifying it (e.g. land masking)"""
    return Path(shutil.copy(combined_tif_from_up42_zip, tmp_path))


@pytest.fixture(scope="session")
def sea_areas(testdata_root: Path) -> gpd.GeoDataFrame:
    """:returns: IHO Adriatic Sea, clipped around `combined_tif_from_up42_zip`.
    Note, the latter's valid pixels (bottom right corner) are all at sea.
    """
    return gpd.read_file(testdata_root / "sea_areas_test_tile.geojson")


@pytest.fixture(scope="session")
def sea_areas_with_island(sea_areas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """:returns: `sea_areas` with an island at the valid pixels (rows 1000-1100, cols 1100-1160, 93.3 m pixels)
    of `combined_tif_from_up42_zip`, to get valid land pixels.
    """
    x0, y0, px = 199980.0, 4700040.0, 280 / 3
    island = box(x0 + 1100 * px, y0 - 1100 * px, x0 + 1160 * px, y0 - 1000 * px)
    island_4326 = gpd.GeoSeries([island], crs="EPSG:32634").to_crs("EPSG:4326").iloc[0]
    with_island = sea_areas.copy()
    with_island["geometry"] = with_island.geometry.difference(island_4326)
    return with_island
