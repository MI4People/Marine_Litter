# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- **ML-047 gap**: `gdal.Translate` in `predict_litter()` now has null-check, `FlushCache()`, and explicit close — matching the pattern applied in `zip_processing.py` and `get_tiff_layout()`
- **ML-049 gap**: Dockerfile now supports optional SHA256 checksum verification for model checkpoint via `MODEL_CKPT_SHA256` build-arg
- **ML-044 tests**: New `TestProductionConstantIntegrity` class verifies `ORDER_TERMINAL_FAILURE_STATES` against actual source (prevents undetected regressions)
- **ML-046 tests**: New `TestNoAssertInProduction` class prevents bare `assert` statements from being reintroduced
- **ML-048 tests**: Added absolute-path ZipSlip test covering `/etc/passwd`-style attacks
- **Code quality**: Removed unused `patch` import, consolidated `Path` imports in test file
