# Changelog
All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-10
### Added
- Land masking before prediction, so that marine litter is only detected on water,
  see [specs/landmask.md](specs/landmask.md) and module `marine_litter.landmask`:
  - IHO Sea Areas around the AOI are fetched from the [Marine Regions](https://www.marineregions.org) WFS once per
    run, with a local copy as fallback. Without both, the run predicts unmasked and logs a warning.
  - Land pixels are filled with the per-band median of the tile's water pixels, a water-like neutral value.
  - Tiles without water are skipped and reported separately in the run summary.
  - Predictions are set to 0 on land.
  - Settings `ML_LANDMASK_ENABLED`, `ML_LANDMASK_BUFFER_M` (default 250 m) and `ML_LANDMASK_PATH`
    (default 'resources/landmask.geojson').
- Feature specification [specs/landmask.md](specs/landmask.md).
- 'scripts/vizualize_tile.py' to view band combinations of downloaded GeoTIFFs.
- Dev container, pre-commit hooks (`uv-lock`, `ruff`, `ty`) and a test coverage report.
- 'scripts/up42_auth_check.py' to check the UP42 credentials.
- This changelog.

### Changed
- The marinedebrisdetector model is loaded once per run instead of once per tile.
- The run summary distinguishes predicted, skipped (no water) and failed tiles.
- Direct dependencies `geopandas`, `numpy`, `rasterio` and `shapely` are declared explicitly.
- Type hints and docstrings throughout, `ty` type checks in strict mode.
- 'src/LandMask.ipynb' uses `marine_litter.landmask`, and 'src/landmask_validation.py' passes the quality checks.
- Settings are validated more strictly (e.g. `ML_DEVICE`, `ML_LOG_LEVEL`, value ranges).
- Documentation links to the Copernicus Browser instead of the retired EO Browser.

### Removed
- 'src/landmask.py', the proof of concept for land masking, superseded by `marine_litter.landmask`.

### Fixed
- GDAL errors raise exceptions instead of passing silently.
- Temporary files of failed predictions and ZIP extractions are cleaned up.
- A missing `TILE_ID` in the metadata of a UP42 ZIP is detected.
- A missing env file no longer loads a file named `None`.

### Security
- ZIP archives are checked against path traversal ("Zip Slip") before extraction.
- Dependencies updated to fix security vulnerabilities.

[Unreleased]: https://github.com/MI4People/Marine_Litter/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/MI4People/Marine_Litter/releases/tag/v0.2.0
