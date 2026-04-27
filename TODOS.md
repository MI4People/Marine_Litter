# Marine Litter — TODO / Issue Backlog

> **Generated:** 2026-03-31 — after full analysis of the codebase vs. [up42-py v3.4.0](https://github.com/up42/up42-py/tree/v3.4.0)
> **Notation:** Priority labels follow `P0` (blocker) → `P3` (nice-to-have). Type labels: `Bug`, `Task`, `Refactor`, `Test`, `Docs`.

---

## Recommended Execution Order

Tasks are grouped into **12 phases** ordered by dependency chains, risk reduction (bugs & security first), and foundation-before-features. Each phase can be a sprint or a batch of PRs.

### Phase 1 — Quick Bug Fixes *(no dependencies, minutes each, immediate risk reduction)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 1 | ML-009 | ~~`cpu_or_cuda.upper` → `.upper()`~~ ✅ | One-line fix, currently logs garbage |
| 2 | ML-043 | ~~TILE_ID XML `find()` off-by-one~~ ✅ | Silent data corruption on malformed XML |
| 3 | ML-045 | ~~`cloud_coverage:5.1f` crashes on `None`~~ ✅ | Runtime crash on SAR scenes |
| 4 | ML-044 | ~~`"FAILED"` → `"FAILED_PERMANENTLY"`~~ ✅ | Failed orders never detected, poll until timeout |
| 5 | ML-046 | ~~Replace `assert` with proper error handling~~ ✅ | Stripped by `python -O` |
| 6 | ML-030 | ~~GEE JS `position == 0` → `= 0`~~ ✅ | No-op assignment in JS prototype |

### Phase 2 — Security Fixes *(high-impact, before any deployment)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 7 | ML-048 | ~~ZipSlip path traversal in `extractall()`~~ ✅ | Security vulnerability, even with trusted source |
| 8 | ML-049 | ~~Model checkpoint over insecure HTTP~~ ✅ | MITM attack vector on ML weights |

### Phase 3 — Remove Hacks & Stabilize Imports *(eliminate fragile patterns before refactoring)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 9 | ML-002 | ~~Remove `MagicMock` → use `UP42_DISABLE_VERSION_CHECK`~~ ✅ | Removes `unittest.mock` from prod; unblocks clean imports |
| 10 | ML-017 | ~~Remove `unittest.mock` from production code~~ ✅ | Depends on ML-002 |
| 11 | ML-003 | ~~Remove logger monkey-patch~~ ✅ | Fragile; may break on SDK update |
| 12 | ML-047 | ~~GDAL dataset leak in `get_tiff_layout()`~~ ✅ | Resource leak, especially in multi-GPU |

### Phase 4 — Configuration & Settings Foundation *(must be done before features that add settings)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 13 | ML-008 | Pin `up42-py~=3.4` in `pyproject.toml` | Lock SDK version before API changes |
| 14 | ML-054 | Fix `MLSettings` string stripping | Fragile `is str` check; remove before adding fields |
| 15 | ML-001 | Auth migration — add `region`, handle `cfg_file` | Core auth must work before anything else |
| 16 | ML-018 | Add `ML_REGION` setting | Needed by ML-001 |
| 17 | ML-014 | Docker-compose env vars: add `ML_` prefix | Settings are silently ignored without this |
| 18 | ML-056 | Fix `run-analysis.sh` (hardcoded paths + prefix) | Same issue as ML-014, different file |
| 19 | ML-036 | Consolidate all parallelism settings via env vars | Foundation for ML-033/035/038 |

### Phase 5 — Code Structure Refactoring *(clean architecture before adding features)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 20 | ML-051 | Replace string `find()` XML with `ElementTree` | Also fixes ML-043 properly; stdlib only |
| 21 | ML-052 | Remove `os.chdir()` + fix bare script imports | Thread-safety; unblocks parallel work |
| 22 | ML-010 | Move UP42 logic from `scripts/` to `src/` | Enables testability & reuse |
| 23 | ML-055 | Add package exports to `__init__.py` | Clean public API |
| 24 | ML-050 | Fix `shutil.rmtree()` — don't destroy all predictions | Data loss risk every run |
| 25 | ML-057 | Narrow `*.tif` deletion glob | Same data safety concern |
| 26 | ML-016 | Remove dead code in `upload_to_gc_storage.py` | Clean up before adding features |
| 27 | ML-053 | Refactor `merge_tiles.py` (hardcoded params, style) | Consistency with rest of codebase |

### Phase 6 — UP42 SDK API Alignment *(requires Phase 3–5 complete)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 28 | ML-005 | Use `Order.track()` instead of custom polling | Removes redundant loop; uses SDK's tenacity |
| 29 | ML-004 | STAC download consistency with v3.4.0 | Verify `collection.assets` vs `item.assets` |
| 30 | ML-006 | Verify `BatchOrderTemplate` estimate-on-construct | Understand cost implications |
| 31 | ML-007 | Add `Order.cancel()` for stuck orders | New capability from v3.4.0 |

### Phase 7 — Logging & Profiling *(foundation for observability)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 32 | ML-031 | Configurable logging (simple/detailed/json) | Must exist before ordered parallel logging |
| 33 | ML-035 | Ordered logging in parallel workers (QueueHandler) | Depends on ML-031 |
| 34 | ML-037 | Lightweight `--timing` flag | Low overhead; good for production cron |
| 35 | ML-032 | Full `--profile` flag (CPU, RSS, GPU memory) | Heavier; for optimization work |

### Phase 8 — Pipeline Refactor & Multi-GPU *(requires Phases 5–7 complete)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 36 | ML-038 | Refactor into `Pipeline` class with stages | Central orchestration for everything below |
| 37 | ML-033 | Multi-GPU support — distribute across H100s | Requires ML-036 (settings) + ML-038 (pipeline) |
| 38 | ML-039 | GPU health check & VRAM guard | Safety before prediction on multi-GPU |
| 39 | ML-034 | Portable Docker — auto-detect CPU vs GPU | Depends on ML-033 (GPU settings exist) |

### Phase 9 — Testing *(validate all prior refactoring)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 40 | ML-011 | Tests for `download_from_up42.py` (0% → 80%) | Most critical untested code |
| 41 | ML-012 | Tests for `predict_litter.py` | Second most critical |
| 42 | ML-013 | Tests for `upload_to_gc_storage.py` | Third priority |

### Phase 10 — Docker & Infrastructure *(requires Phases 4, 8, 9)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 43 | ML-015 | Remove deprecated `version` in docker-compose | Quick cleanup |
| 44 | ML-020 | Clarify Dockerfile `COPY` paths | Avoid confusion |
| 45 | ML-040 | Docker healthcheck & resource limits | Production readiness |
| 46 | ML-019 | Add `--env-file` CLI argument to all scripts | Flexibility for Docker/CI |

### Phase 11 — Documentation *(document the stabilized system)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 47 | ML-022 | Update Docker readme for current `MLSettings` | Stale docs |
| 48 | ML-023 | Fix Python version inconsistency in README | Quick fix |
| 49 | ML-024 | Document UP42 SDK dependency and version | Users need to know |
| 50 | ML-042 | Deployment scenarios (local/single-GPU/multi-GPU) | Key operational doc |
| 51 | ML-025 | Add architecture diagram | Nice-to-have visualization |

### Phase 12 — Future Enhancements *(nice-to-have, no blockers)*
| # | ID | Title | Rationale |
|---|------|-------|-----------|
| 52 | ML-026 | Deduplicate orders via `Order.all()` | Cost savings |
| 53 | ML-027 | Tag orders for traceability | Observability |
| 54 | ML-041 | Structured JSON pipeline run report | Monitoring |
| 55 | ML-028 | Explore UP42 processing jobs | Research/POC |
| 56 | ML-029 | GEE prototype automation | Research/POC |
| 57 | ML-021 | Add GitHub Actions CI pipeline | DevOps maturity |

---

> **Detailed task descriptions** are below, organized by functional epic for reference. Use the phase table above for execution order.

---

## Epic 1 — UP42 SDK v3 Migration & Compatibility

### ML-001 · [P0 / Bug] `authenticate()` no longer accepts `username` / `password` — migrate to SDK credentials

**Description**
The project's `authenticate_with_up42()` in `scripts/download_from_up42.py` (line 82) calls:
```python
authenticate(username=creds.get("username"), password=creds.get("password"))
```
In **up42-py v3.4.0** the `authenticate()` signature is:
```python
def authenticate(
    cfg_file: str | pathlib.Path | None = None,
    username: str | None = None,
    password: str | None = None,
    region: Literal["eu", "sa"] = "eu",
)
```
While `username`/`password` keyword arguments are still present, the SDK now also supports `region` and `cfg_file`. More critically, UP42 itself has been transitioning from username/password credentials toward **project-level API keys**. The current code reads a JSON with `username` + `password`, which may break with future SDK/API changes.

**Acceptance Criteria**
- [ ] `authenticate_with_up42()` optionally passes the `cfg_file` path directly or keeps the current `username`/`password` approach but adds a `region` parameter (default `"eu"`).
- [ ] `secrets/up42_credentials.json` schema is documented in `.example.env` and `docker/readme.md`.
- [ ] A fallback or error message is shown when the credential format is unrecognised.
- [ ] Add `region` setting to `MLSettings` (default `"eu"`, options `"eu"` | `"sa"`).
- [ ] `.example.env` updated with `ML_REGION=eu`.
- [ ] Tests cover both `cfg_file` and `username/password` auth paths (mocked).

**Technical Notes**
- `base.py` in v3.4.0: `host.REGION = region` is set globally; ensure the project sets this before any other SDK call.
- Credentials could also contain `cfg_file` path instead of inline `username`/`password`.
- `up42.host.py` now uses region-aware endpoints (`api.up42.com` vs `api.sa.up42.com`).

---

### ML-002 · [P0 / Bug] Version check mock `MagicMock` is fragile — use official `UP42_DISABLE_VERSION_CHECK` env var

**Description**
`scripts/download_from_up42.py` (lines 23–26) patches the UP42 version check with:
```python
if "up42.version.version_control" not in sys.modules:
    sys.modules["up42.version.version_control"] = MagicMock(check_package_version=MagicMock())
```
Since **up42-py v3.2.0**, the SDK supports an official environment variable `UP42_DISABLE_VERSION_CHECK` to disable this check. The `MagicMock` approach is brittle, relies on `unittest.mock` in production code, and can mask import-time errors.

**Acceptance Criteria**
- [x] Remove the `MagicMock` hack from `download_from_up42.py`. *(done: replaced with `os.environ.setdefault("UP42_DISABLE_VERSION_CHECK", "true")`)*
- [x] Set `UP42_DISABLE_VERSION_CHECK=1` via `.env` / Docker environment. *(done: set in Python code + `docker-compose.yml`)*
- [x] `.example.env` documents this variable. *(done: documented as comment — cannot be a live variable due to `MLSettings(extra='forbid')`)*
- [x] Docker/`docker-compose.yml` sets this env var. *(done: `docker-compose.yml` environment section)*
- [x] Import of `up42` works cleanly without any `sys.modules` manipulation. *(done: direct import after env var set)*

**Technical Notes**
- Changelog v3.2.0a6: _"Check environment variable UP42_DISABLE_VERSION_CHECK to disable checking the latest SDK version based on its value."_
- The `up42/__init__.py` v3.4.0 still calls `version_control.check_is_latest_version(__version__)` — the env var gates this internally.
- Consider also relocating the UP42 imports to top-level once the mock is removed.

---

### ML-003 · [P0 / Bug] Logger monkey-patch `utils.get_logger` is fragile — replace with standard logging config

**Description**
`scripts/download_from_up42.py` (lines 31–43) overrides `up42.utils.get_logger` to make UP42 loggers propagate to the root logger. This is fragile because:
1. The function signature must match the SDK's exactly.
2. SDK updates could change or rename the function.
3. A cleaner approach is to configure the `"up42"` logger hierarchy via Python's standard `logging` module after import.

**Acceptance Criteria**
- [x] Remove the `_patched_get_logger` function and `utils.get_logger` reassignment. *(done: no monkey-patching exists)*
- [x] After `import up42`, reconfigure UP42 loggers properly: *(done: root `"up42"` logger + child loggers reconfigured)*
  ```python
  up42_logger = logging.getLogger("up42")
  up42_logger.handlers.clear()
  up42_logger.propagate = True
  ```
- [x] Logging output from UP42 SDK appears in the project's standard format. *(done: propagation ensures root handler format is used)*
- [x] Log level is respected per `MLSettings.log_level`. *(done: propagation + NOTSET on `up42` logger inherits root level)*

**Technical Notes**
- `up42.utils.get_logger()` in v3.4.0 still creates its own `StreamHandler` with `propagate = False`. The cleanest fix is to reconfigure after import.
- This is a post-import one-time operation, not a monkey-patch.

---

### ML-004 · [P1 / Refactor] `_download_single_order()` uses the STAC client API inconsistently with v3.4.0

**Description**
`scripts/download_from_up42.py` lines 157–169, `_download_single_order()` uses:
```python
items = stac_client().search(filter={"op": "=", "args": [{"property": "order_id"}, order.id]})
for item in items.items():
    collection = item.get_collection()
    ...
    assets: ValuesView[Asset] = collection.assets.values()
    order_asset = next((asset for asset in assets if asset.roles and "original" in asset.roles), None)
    if order_asset:
        downloaded_file_path = order_asset.file.download(output_directory=download_dir)
```

In **up42-py v3.4.0**, the `pystac.Asset.file` descriptor (`FileProvider` in `stac.py`) returns a `utils.ImageFile` whose `download()` method returns a `pathlib.Path`, not a string. The code variable naming (`downloaded_file_path`) suggests this is expected but should be explicitly validated.

Additionally, `collection.assets` refers to `pystac.Collection.assets` — it's unclear whether the UP42 STAC API returns collections with a downloadable "original" asset at the collection level, or if the code should look at `item.assets` instead.

**Acceptance Criteria**
- [ ] Verify the download path works end-to-end with up42-py ≥ 3.4.0.
- [ ] Confirm whether `collection.assets` or `item.assets` is the correct lookup target.
- [ ] Add error handling for the case where `order_asset.file` returns `None` (happens when `href` doesn't start with the UP42 API base URL, per `FileProvider.__get__`).
- [ ] Add a unit test for `_download_single_order()` with mocked STAC client.

**Technical Notes**
- `stac.py` v3.4.0 `FileProvider.__get__` checks `obj.href.startswith(host.endpoint(""))` — if the href isn't an UP42 URL, it returns `None`, which would cause an `AttributeError` on `.download()`.
- `utils.ImageFile.download()` returns `pathlib.Path`.

---

### ML-005 · [P1 / Refactor] `Order.track()` in v3.4.0 uses `tenacity` internally — remove custom polling loop

**Description**
`scripts/download_from_up42.py` lines 172–197, `_process_single_order()` implements a custom polling loop:
```python
while not order.is_fulfilled and order.status != "FAILED":
    await asyncio.sleep(6.0)
    order = await asyncio.to_thread(Order.get, order.id)
    order.track()
```
In **up42-py v3.4.0**, `Order.track()` already implements `tenacity`-based retry with `wait_fixed(report_time)` and handles `FAILED_PERMANENTLY`, `CANCELED`, and unfulfilled states internally. Calling `order.track()` inside a manual polling loop is redundant and may cause double-waiting (6s sleep + `tenacity`'s 120s wait).

**Acceptance Criteria**
- [ ] Replace the manual `asyncio` polling loop with a direct call to `Order.track()`.
- [ ] Wrap `Order.track()` in `asyncio.to_thread()` for async concurrency.
- [ ] Handle `FailedOrder`, `CanceledOrder`, and `UnfulfilledOrder` exceptions from `Order.track()`.
- [ ] Remove the manual timeout logic (or configure `tenacity` params if needed).
- [ ] Download step should only run after `track()` returns successfully.

**Technical Notes**
- `Order.track()` raises `FailedOrder` on `FAILED_PERMANENTLY`, `CanceledOrder` on `CANCELED`, stays in retry on unfulfilled.
- `Order.track(report_time=120)` — the project may want to use a shorter `report_time`.
- `Order.track()` mutates the order object in-place (`setattr`).

---

### ML-006 · [P1 / Task] Verify `BatchOrderTemplate` usage against v3.4.0 — `__post_init__` calls estimate

**Description**
`scripts/download_from_up42.py` lines 223–237, `place_orders()` creates a `BatchOrderTemplate`:
```python
order_template = BatchOrderTemplate(
    data_product_id=product_info.product_id,
    display_name=f"{scene.id}",
    features=features,
    params={"id": scene.id},
)
got: list[OrderReference | OrderError] = order_template.place()
```
In **up42-py v3.4.0**, `BatchOrderTemplate.__post_init__()` immediately calls `self.__estimate()`, which performs a **POST to `/v2/orders/estimate`**. This means every template instantiation triggers a network call, even if you only want to place. This is the intended SDK behaviour but has cost/performance implications.

**Acceptance Criteria**
- [ ] Confirm the estimate call is acceptable (it does not incur real costs).
- [ ] Add logging of the estimate result (credits, size) before placing the order.
- [ ] Handle potential `OrderError` items in the estimate response.
- [ ] Add error handling around `BatchOrderTemplate` construction (network errors on estimate).

**Technical Notes**
- `BatchOrderTemplate._payload` excludes `tags` when `None`, which the project already handles (tags not passed).
- `OrderReference.order` is a property that calls `Order.get(self.id)` — another network call.

---

### ML-007 · [P2 / Task] Add `Order.cancel()` support for stuck/failed orders

**Description**
The pipeline currently has no mechanism to cancel orders that get stuck. In v3.4.0, `Order` has a `cancel()` method that works for orders in `CREATED` or `PLACEMENT_FAILED` status.

**Acceptance Criteria**
- [ ] Add a `--cancel-stuck` CLI flag to `download_from_up42.py` that finds and cancels orders in `CREATED` or `PLACEMENT_FAILED` status older than a threshold.
- [ ] Use `Order.all(status=["CREATED", "PLACEMENT_FAILED"])` + `order.cancel()`.
- [ ] Log the cancellation results.

**Technical Notes**
- `Order.cancel()` raises `OrderCannotBeCanceled` if the order is in an invalid status.
- `Order.all()` supports filtering by `status`, `order_type`, `tags`, etc.

---

### ML-008 · [P2 / Task] Pin `up42-py` version to `~=3.4.0` in `pyproject.toml`

**Description**
Currently `pyproject.toml` requires `up42-py>=3` which is very broad. The codebase uses v3-specific APIs (`BatchOrderTemplate`, `ProductGlossary`, `Provider.search`, etc.) that may break with future major changes.

**Acceptance Criteria**
- [ ] Change `up42-py>=3` to `up42-py~=3.4` (compatible release: ≥3.4, <4.0).
- [ ] Run `uv sync --upgrade` and verify lock file updates.
- [ ] All existing tests pass.

**Technical Notes**
- The `~=3.4` specifier allows patches (3.4.1, 3.5.0, etc.) but blocks 4.0+.
- This prevents silent breakage when UP42 releases v4.

---

## Epic 2 — Code Quality & Bug Fixes

### ML-009 · [P0 / Bug] `predict_litter()` in `tif_processing.py` has `cpu_or_cuda.upper` (missing parentheses)

**Description**
`src/marine_litter/tif_processing.py` line 25:
```python
log.info(f"Predict '{tif_file.name}' using {cpu_or_cuda.upper}")
```
`str.upper` is a method — this logs the **method object** (e.g. `<built-in method upper of str object at 0x…>`) instead of `"CUDA"` or `"CPU"`. Should be `cpu_or_cuda.upper()`.

**Acceptance Criteria**
- [x] Fix to `cpu_or_cuda.upper()`. *(done: `tif_processing.py:25`)*
- [x] Add a test that validates the log message content. *(done: `test_predict_litter_log_message_shows_uppercased_device`, `test_predict_litter_log_message_cpu`)*

**Technical Notes**
- Simple one-line fix but this indicates insufficient test coverage for the log output of `predict_litter()`.

---

### ML-010 · [P1 / Refactor] Move UP42-specific logic from `scripts/` into `src/marine_litter/`

**Description**
The core UP42 download logic (`authenticate_with_up42`, `fetch_collections`, `determine_product_info`, `determine_scenes`, `place_orders`, `process_orders_concurrently`, `_download_single_order`) is all in `scripts/download_from_up42.py` (a script file, not a package module). This makes it:
- Untestable without importing a script.
- Not distributable with the `marine-litter` package.
- Difficult to reuse.

**Acceptance Criteria**
- [ ] Create `src/marine_litter/up42_download.py` containing all UP42 logic.
- [ ] `scripts/download_from_up42.py` becomes a thin CLI wrapper that imports from the package.
- [ ] All UP42 dataclasses (`ProductInfo`, `SceneSearchParams`) move to the package.
- [ ] Unit tests can import `marine_litter.up42_download` directly.
- [ ] Minimum 80% test coverage for the extracted module (with mocked UP42 calls).

**Technical Notes**
- Same pattern should be applied to `scripts/predict_litter.py` (already partially done — it imports from `marine_litter.tif_processing` and `marine_litter.zip_processing`) and `scripts/upload_to_gc_storage.py`.
- `scripts/merge_tiles.py` could also be refactored but is lower priority.

---

### ML-011 · [P1 / Test] Add tests for `scripts/download_from_up42.py` — currently 0% coverage

**Description**
The file `scripts/download_from_up42.py` (303 lines, the largest and most critical file in the project) has **zero test coverage**. It contains 8 functions including authentication, scene search, ordering, polling, and download logic. All UP42 API interactions are untested.

**Acceptance Criteria**
- [ ] Create `tests/test_download_from_up42.py`.
- [ ] Test `authenticate_with_up42()`: success, bad JSON, bad credentials.
- [ ] Test `fetch_collections()`: returns collections, returns empty.
- [ ] Test `determine_product_info()`: product found, product not found.
- [ ] Test `determine_scenes()`: scenes found, no scenes, filtering by cloud cover.
- [ ] Test `place_orders()`: success, `OrderError` response.
- [ ] Test `_download_single_order()`: asset found, asset not found.
- [ ] Test `main()`: dry-run, tell-only, full flow (mocked).
- [ ] All UP42 API calls are mocked (no real network calls).
- [ ] Coverage ≥ 80%.

**Technical Notes**
- Use `unittest.mock.patch` to mock `up42.authenticate`, `up42.stac_client`, `ProductGlossary.get_collections`, etc.
- Consider using `pytest-mock` for cleaner mocking.

---

### ML-012 · [P1 / Test] Add tests for `scripts/predict_litter.py`

**Description**
`scripts/predict_litter.py` (132 lines) has no unit tests. It contains `show_progress()`, `move_predictions_and_remove_prediction_input_files()`, `update_dates_json()`, and `main()`.

**Acceptance Criteria**
- [ ] Create `tests/test_predict_litter.py`.
- [ ] Test `move_predictions_and_remove_prediction_input_files()`: moves files, handles errors.
- [ ] Test `update_dates_json()`: creates new file, appends to existing, handles corrupt JSON.
- [ ] Test `main()`: dry-run path, no-zip-files path, normal flow (mocked prediction).
- [ ] Coverage ≥ 80%.

**Technical Notes**
- `update_dates_json()` has a regex `r"_(20\d{2})(\d{2})(\d{2})T\d{6}_"` for date extraction — test edge cases.
- `process_zip` and `predict_litter` can be mocked to avoid GDAL/GPU dependencies.

---

### ML-013 · [P1 / Test] Add tests for `scripts/upload_to_gc_storage.py`

**Description**
`scripts/upload_to_gc_storage.py` (81 lines) has no unit tests. It interfaces with Google Cloud Storage.

**Acceptance Criteria**
- [ ] Create `tests/test_upload_to_gc_storage.py`.
- [ ] Test `upload_delete()`: successful upload, upload error, missing source folder.
- [ ] Test `main()`: dry-run path.
- [ ] All GCS calls are mocked.
- [ ] Coverage ≥ 80%.

**Technical Notes**
- Mock `google.cloud.storage.Client.from_service_account_json`, `bucket.blob`, etc.

---

### ML-014 · [P2 / Bug] `docker-compose.yml` env vars missing `ML_` prefix

**Description**
`docker/docker-compose.yml` sets environment variables without the `ML_` prefix:
```yaml
environment:
  - DAYS_BEFORE=2
  - PREDICT_WORKERS=3
  - ORDER_WORKERS=10
  - DEVICE=cuda
```
But `MLSettings` uses the `ML_` prefix (`_env_prefix="ML_"`). These environment variables are **silently ignored**.

**Acceptance Criteria**
- [ ] Change to `ML_DAYS_BEFORE`, `ML_PREDICT_WORKERS`, `ML_ORDER_WORKERS`, `ML_DEVICE`.
- [ ] Update `docker/readme.md` to document the `ML_` prefix.
- [ ] Update `docker/run-analysis.sh` similarly.
- [ ] Test that Dockerised settings are correctly loaded.

**Technical Notes**
- `pydantic_settings` only reads env vars matching the prefix (case-insensitive).
- `run-analysis.sh` also uses unprefixed env vars.

---

### ML-015 · [P2 / Bug] `docker-compose.yml` uses deprecated `version` key

**Description**
`docker/docker-compose.yml` line 1 has `version: "3.8"`. Docker Compose V2 ignores this key and prints a deprecation warning. Additionally, the `volumes` paths are hardcoded to `/home/demo1/...`.

**Acceptance Criteria**
- [ ] Remove the `version: "3.8"` line.
- [ ] Replace hardcoded volume paths with relative paths or environment variables.
- [ ] Use `env_file: ../.env` to load settings from the `.env` file.

**Technical Notes**
- Docker Compose V2 docs: _"The version property is obsolete."_

---

### ML-016 · [P2 / Refactor] `upload_to_gc_storage.py` contains dead code block

**Description**
Lines 53–57 of `scripts/upload_to_gc_storage.py`:
```python
if not "unclear why this is needed, and how to sort":
    max_results = 100
    ...
```
This condition is always `False` (negation of a truthy string). It's dead code with a comment suggesting it was meant to be temporary.

**Acceptance Criteria**
- [ ] Remove the dead code block or document and enable it behind a flag.
- [ ] If listing is desired, add a `--list-bucket` CLI option.

---

### ML-017 · [P2 / Refactor] `download_from_up42.py` uses `from unittest.mock import MagicMock` in production code

**Description**
Beyond the version-check mock (ML-002), the import of `unittest.mock.MagicMock` in production script code is an anti-pattern. Once ML-002 is resolved, this import can be removed entirely.

**Acceptance Criteria**
- [x] No `unittest.mock` imports exist in any `scripts/*.py` or `src/**/*.py` file. *(verified: zero occurrences)*

**Technical Notes**
- Depends on ML-002 being completed first.

---

## Epic 3 — Configuration & Infrastructure

### ML-018 · [P1 / Task] Add `ML_REGION` setting for UP42 regional endpoints

**Description**
UP42 v3.4.0 supports regional endpoints (`eu` and `sa` — South America). The current project hardcodes EU. A setting should be added to allow switching regions.

**Acceptance Criteria**
- [ ] Add `region: str = Field(default="eu", description="UP42 region: eu|sa")` to `MLSettings`.
- [ ] Pass `region=settings.region` to `authenticate()`.
- [ ] `.example.env` updated with `ML_REGION=eu`.
- [ ] `test_ml_settings.py` updated to test this field.
- [ ] `test_settings_defaults()` and `test_example_env_completeness()` updated.

**Technical Notes**
- `host.py` v3.4.0 raises `UnsupportedRegion` for unknown regions.

---

### ML-019 · [P2 / Task] Add `--env-file` CLI argument to all scripts

**Description**
All scripts currently hardcode `".env"` as the env file path. For Docker and CI/CD, it would be useful to specify a different path.

**Acceptance Criteria**
- [ ] Add `--env-file` argument to `download_from_up42.py`, `predict_litter.py`, `upload_to_gc_storage.py`, `run_all.py`.
- [ ] Default to `.env` if it exists, `None` otherwise (current behaviour in `run_all.py`).
- [ ] Consistent behaviour across all scripts.

---

### ML-020 · [P2 / Task] Dockerfile `COPY ../` paths rely on build context — may break

**Description**
`docker/Dockerfile` uses `COPY ../pyproject.toml .` and similar paths. These only work when `docker build` is run from the project root with `-f docker/Dockerfile`. The `..` in COPY is not relative to the Dockerfile but to the build context.

**Acceptance Criteria**
- [ ] Validate that the documented `docker build -f docker/Dockerfile -t marine_litter .` works correctly.
- [ ] Add a CI test or Makefile target that builds the Docker image.
- [ ] Consider using `.dockerignore` to exclude unnecessary files.

**Technical Notes**
- When build context is `.` (project root), `COPY ../pyproject.toml .` actually resolves to `COPY pyproject.toml .` relative to the build context — the `../` is silently stripped. This is correct but confusing. Consider removing the `../` prefix for clarity.

---

### ML-021 · [P3 / Task] Add GitHub Actions CI pipeline

**Description**
The project has no CI/CD pipeline. There are no `.github/workflows/` files.

**Acceptance Criteria**
- [ ] Create `.github/workflows/ci.yml` that:
  - Installs `uv` and Python 3.12+.
  - Runs `uv sync`.
  - Runs `ruff check`.
  - Runs `ty check`.
  - Runs `pytest tests/`.
- [ ] Pipeline triggers on push and PR to `main`.
- [ ] Badge added to `README.md`.

---

## Epic 4 — Documentation

### ML-022 · [P1 / Docs] Update Docker readme and docker-compose for current MLSettings

**Description**
`docker/readme.md` references `ML_CONFIG_PATH` which does not exist in `MLSettings`. The env var list is incomplete and doesn't match the actual settings.

**Acceptance Criteria**
- [ ] Replace `ML_CONFIG_PATH` with the correct setting names.
- [ ] List all relevant `MLSettings` fields in the Docker readme.
- [ ] Add example `.env` values for Docker usage.
- [ ] Document the `ML_` prefix requirement.

---

### ML-023 · [P2 / Docs] Rename the prerequisite Python version in README

**Description**
`README.md` line 11 says `Python ≥3.11` but `pyproject.toml` requires `>=3.12.3,<3.14`. These are inconsistent.

**Acceptance Criteria**
- [ ] Update `README.md` to say `Python ≥ 3.12.3`.
- [ ] Ensure `docker/readme.md` also matches.

---

### ML-024 · [P2 / Docs] Document UP42 API dependency and version expectations

**Description**
The project heavily depends on UP42's Python SDK but there is no documentation about which SDK version/API features are used and what might break.

**Acceptance Criteria**
- [ ] Add a "Dependencies" section to `docs/index.md` or `README.md`.
- [ ] List UP42 SDK version requirements and major APIs used.
- [ ] Link to UP42 SDK changelog: `https://github.com/up42/up42-py/blob/main/CHANGELOG.md`.
- [ ] Note the `UP42_DISABLE_VERSION_CHECK` env var.

---

### ML-025 · [P3 / Docs] Add architecture diagram to documentation

**Description**
The existing Mermaid diagram in `docs/index.md` covers the pipeline flow but doesn't show the code architecture (modules, classes, dependencies).

**Acceptance Criteria**
- [ ] Add a Mermaid class/module diagram showing:
  - `marine_litter` package modules.
  - External dependencies (up42, GDAL, torch, GCS).
  - Data flow between scripts.
- [ ] Place in `docs/index.md` or a new `docs/architecture.md`.

---

## Epic 5 — Future Enhancements

### ML-026 · [P3 / Task] Use UP42's `Order.all()` to check for existing/duplicate orders

**Description**
Currently the pipeline always places new orders without checking if an identical order already exists. UP42 v3.4.0 provides `Order.all()` with filtering by `display_name`, `tags`, and `status`.

**Acceptance Criteria**
- [ ] Before placing an order for a scene, check if an order with the same `display_name` (scene ID) already exists and is in a non-failed status.
- [ ] Skip placing if an existing order is `PLACED`, `BEING_FULFILLED`, or `FULFILLED`.
- [ ] Re-download if order is `FULFILLED` but the file is missing locally.
- [ ] Log the decision.

**Technical Notes**
- `Order.all(display_name=scene.id, status=["PLACED", "BEING_FULFILLED", "FULFILLED"])`.
- This prevents duplicate charges and wasted API calls.

---

### ML-027 · [P3 / Task] Use UP42 `Order.update()` to tag orders for traceability

**Description**
UP42 v3.4.0 supports `Order.update(order_id, tags=[...])`. The project can tag orders with metadata like `marine-litter`, a run timestamp, or the geojson region name.

**Acceptance Criteria**
- [ ] After placing an order, tag it with `["marine-litter", "<YYYY-MM-DD>"]`.
- [ ] Support custom tags via `MLSettings.order_tags` field.
- [ ] Tags are used in deduplication logic (ML-026).

---

### ML-028 · [P3 / Task] Explore UP42 processing jobs for server-side image processing

**Description**
UP42 v3.4.0 added `Job`, `JobSorting`, `JobStatus` and processing templates (`TrueColorConversion`, `UpsamplingNS`, etc.). The project currently downloads images and processes them locally with GDAL + PyTorch. Some pre-processing (like upsampling or true-color conversion) could potentially be offloaded to UP42's processing API.

**Acceptance Criteria**
- [ ] Investigate which UP42 processing templates are relevant for marine litter detection.
- [ ] Document findings in a design doc.
- [ ] If viable, create a POC that uses UP42 processing as a pipeline step.

**Technical Notes**
- This is an exploration task, not a commitment to change the pipeline.
- Available templates: `TrueColorConversion`, `UpsamplingNS`, `UpsamplingNSSentinel`, `DetectionChangeSimularity`, `CoregistrationJobTemplate`.

---

### ML-029 · [P3 / Task] Add GEE prototype automation — auto-update region data from predictions

**Description**
`web_gee/GEE-Prototype.js` has hardcoded regions and timepoints. The pipeline uploads predictions to GCS, but there's no automation to update the GEE app with new regions/dates.

**Acceptance Criteria**
- [ ] Design a mechanism to generate `regionArray` data from `dates.json` and GCS bucket contents.
- [ ] Automate the update of GEE app configuration after new predictions are uploaded.
- [ ] Document the process.

---

### ML-030 · [P3 / Refactor] `GEE-Prototype.js` — fix minor issues

**Description**
`web_gee/GEE-Prototype.js` line 111: `position == 0;` uses comparison (`==`) instead of assignment (`=`). It's a no-op.

**Acceptance Criteria**
- [x] Fix `position == 0;` to `position = 0;` (or remove if not needed). *(done: `GEE-Prototype.js:111`)*
- [ ] ~~Add JavaScript linting configuration (e.g., ESLint).~~ *(deferred: GEE scripts run in Google's Earth Engine code editor, not a standard Node.js environment — ESLint is not applicable)*

---

## Epic 6 — Logging, Profiling, Multi-GPU & Docker Portability

### ML-031 · [P0 / Task] Implement configurable logging verbosity levels with structured output

**Description**
The current logging setup uses `basicConfig` with a single format string and level. For production use on a multi-GPU VM and for debugging, the project needs multiple selectable logging profiles with structured output, including timestamps, process/thread IDs (critical for parallel work), and optional JSON output for log aggregation tools.

**Acceptance Criteria**
- [ ] Add `ML_LOG_MODE` setting to `MLSettings` with options: `simple` | `detailed` | `json`.
  - `simple`: Current behaviour — human-readable, single-line, minimal context.
  - `detailed`: Includes timestamp, log level, module, function name, line number, process ID, thread ID.
  - `json`: JSON Lines format (one JSON object per log entry) for machine parsing — includes all fields from `detailed` plus structured key-value data.
- [ ] Add `ML_LOG_FILE` setting (default: empty = stdout only). When set, logs are written to both stdout and the specified file (using `logging.FileHandler`).
- [ ] Add `ML_LOG_ROTATE` setting (default: `false`). When `true` and `ML_LOG_FILE` is set, use `RotatingFileHandler` with 10 MB max size, 5 backup files.
- [ ] All loggers (project + UP42 SDK) respect the configured mode.
- [ ] CLI flag `--log-mode` / `-m` added to all scripts to override `ML_LOG_MODE`.
- [ ] `.example.env` updated with new settings.
- [ ] Tests cover all three modes and verify output format.

**Technical Notes**
- `detailed` format example: `2026-03-31 10:00:00.123 | INFO | PID:1234 | TID:main | download_from_up42.py:main:82 | Placing 5 order(s)...`
- `json` format example: `{"ts":"2026-03-31T10:00:00.123Z","level":"INFO","pid":1234,"tid":"main","module":"download_from_up42","func":"main","line":82,"msg":"Placing 5 order(s)..."}`
- Python's `logging.Formatter` supports `%(process)d`, `%(thread)d`, `%(threadName)s`.
- For JSON mode, use `python-json-logger` or a custom `logging.Formatter` subclass — avoid adding a heavy dependency.
- Consider a `setup_logging()` function in `src/marine_litter/logging_config.py` that all scripts call.

---

### ML-032 · [P0 / Task] Add per-process timing and resource profiling via `--profile` flag

**Description**
Each pipeline stage (download, zip processing, prediction, upload) should optionally report execution time, peak memory usage, GPU memory usage (if CUDA), and CPU utilisation. This is essential for optimizing performance on the H100 VM and for capacity planning.

**Acceptance Criteria**
- [ ] Add `--profile` / `-p` CLI flag to `run_all.py`, `download_from_up42.py`, `predict_litter.py`, `upload_to_gc_storage.py`.
- [ ] When `--profile` is active, each major function is wrapped to report:
  - **Wall-clock time** (start → end).
  - **CPU time** (user + system via `time.process_time()` or `resource.getrusage()`).
  - **Peak RSS memory** (via `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` on Linux).
  - **GPU memory** (via `torch.cuda.max_memory_allocated()` / `torch.cuda.memory_summary()`) — only when `device=cuda`.
- [ ] Profile data is logged at `INFO` level and optionally written to a JSON summary file (`ML_PROFILE_OUTPUT` setting, default: empty = log only).
- [ ] A reusable `@profile_step(name)` decorator or context manager is implemented in `src/marine_litter/profiling.py`.
- [ ] Per-file prediction timing is logged (e.g., `Predicted 'scene_xyz.tif' in 42.3s, GPU peak: 12.4 GB`).
- [ ] Pipeline summary at end of `run_all.py`: total time, per-stage breakdown.
- [ ] Add `ML_PROFILE_OUTPUT` to `MLSettings` and `.example.env`.

**Technical Notes**
- Example summary output:
  ```
  ┌─────────────────────┬──────────┬───────────┬───────────────┬──────────────┐
  │ Stage               │ Wall (s) │ CPU (s)   │ Peak RSS (MB) │ GPU Peak (MB)│
  ├─────────────────────┼──────────┼───────────┼───────────────┼──────────────┤
  │ Download (5 scenes) │   912.3  │    45.2   │       320     │      —       │
  │ Zip Processing      │    23.7  │    22.1   │       890     │      —       │
  │ Prediction (5 tifs) │   187.4  │   178.9   │      2,340    │   11,200     │
  │ Upload              │    34.1  │     8.3   │       280     │      —       │
  ├─────────────────────┼──────────┼───────────┼───────────────┼──────────────┤
  │ TOTAL               │  1157.5  │   254.5   │      2,340    │   11,200     │
  └─────────────────────┴──────────┴───────────┴───────────────┴──────────────┘
  ```
- On Linux, `ru_maxrss` is in kilobytes; on macOS it's bytes — normalise.
- `torch.cuda.reset_peak_memory_stats()` should be called before each stage for accurate per-stage measurements.
- Use `contextlib.contextmanager` for the profiling context or a decorator — whichever is cleaner.

---

### ML-033 · [P0 / Task] Multi-GPU support — distribute prediction across multiple NVIDIA GPUs

**Description**
The target deployment is an Ubuntu Linux VM with **multiple NVIDIA H100 GPUs**. Currently `predict_litter()` uses a single `device` string (`"cpu"` or `"cuda"`) and `predict_litter.py` uses `ThreadPoolExecutor` — all workers share the same GPU. For multi-GPU, each worker should be assigned a specific GPU.

**Acceptance Criteria**
- [ ] Add `ML_GPU_IDS` setting to `MLSettings`: comma-separated GPU indices (default: `""` = auto-detect all available, or `"0"` for single GPU). Example: `ML_GPU_IDS=0,1,2,3`.
- [ ] When `ML_GPU_IDS` is set and `ML_DEVICE=cuda`, prediction workers are distributed round-robin across the specified GPUs.
- [ ] Each prediction worker calls `torch.cuda.set_device(gpu_id)` and uses `cuda:{gpu_id}` as the device string.
- [ ] `ML_PREDICT_WORKERS` defaults to the number of available GPUs when `device=cuda` and `ML_GPU_IDS` is not explicitly set.
- [ ] Add GPU diagnostics at startup: log each GPU's name, VRAM, compute capability.
- [ ] `predict_litter()` in `tif_processing.py` accepts a full device string like `"cuda:0"`, `"cuda:1"`, etc.
- [ ] The `run_all.py` startup info (lines 25–31) is extended to list all configured GPUs.
- [ ] Tests verify round-robin assignment logic (mocked, no real GPUs needed).

**Technical Notes**
- `torch.cuda.device_count()` returns the number of visible GPUs.
- `CUDA_VISIBLE_DEVICES` env var can also restrict GPUs — document interaction with `ML_GPU_IDS`.
- H100 has 80 GB HBM3 — multiple large TIFFs can be processed in parallel if each worker uses its own GPU.
- `ProcessPoolExecutor` may be needed instead of `ThreadPoolExecutor` to avoid GIL issues with CUDA contexts across threads — or use `torch.multiprocessing`.
- Consider: if `ML_PREDICT_WORKERS > len(ML_GPU_IDS)`, multiple workers share a GPU (acceptable but should be documented).
- `torch.hub.load` may download model weights — ensure only one process downloads and others wait (use a file lock).

---

### ML-034 · [P1 / Task] Portable Docker setup — auto-detect CPU vs GPU at runtime

**Description**
The Docker image must work on:
1. **Production**: Ubuntu VM with multiple NVIDIA H100 GPUs (`--gpus=all`).
2. **Local dev**: Any machine with Docker — CPU-only, single GPU, or no NVIDIA driver.

Currently `docker-compose.yml` hardcodes `driver: nvidia` and `count: all`, which fails on machines without NVIDIA GPUs/driver.

**Acceptance Criteria**
- [ ] Create **two** docker-compose profiles (or separate files):
  - `docker-compose.yml` — base, no GPU requirements, works everywhere.
  - `docker-compose.gpu.yml` — extends base, adds `deploy.resources.reservations.devices` for NVIDIA GPUs.
- [ ] Usage:
  - CPU-only: `docker compose up`
  - With GPUs: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`
- [ ] `ML_DEVICE` defaults to `cpu` in the base compose; overridden to `cuda` in the GPU compose.
- [ ] At startup, `run_all.py` logs whether CUDA is available and falls back gracefully:
  ```
  [INFO] CUDA not available — running on CPU (prediction will be slower)
  ```
  or:
  ```
  [INFO] CUDA available — 4x NVIDIA H100 80GB HBM3 detected
  ```
- [ ] Dockerfile does **not** install NVIDIA drivers (these come from the host via `nvidia-container-toolkit`).
- [ ] Docker readme updated with CPU-only and GPU usage instructions.
- [ ] Test: build and run on a machine without GPUs — should not crash.

**Technical Notes**
- The existing `FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.4` base image does NOT include CUDA. The PyTorch wheels with `cu130` suffix include the CUDA runtime but still need the host NVIDIA driver.
- `torch.cuda.is_available()` is the runtime check — it returns `False` if no GPU/driver is present.
- Docker Compose V2 profiles: `services.marine_litter.profiles: ["gpu"]` can also be used instead of separate files.

---

### ML-035 · [P1 / Task] Refactor parallel processing — use `ProcessPoolExecutor` with ordered logging

**Description**
Currently `predict_litter.py` uses `ThreadPoolExecutor` and `download_from_up42.py` uses `asyncio.gather`. When running in parallel, log messages from different workers interleave unpredictably, making debugging very difficult. Logs should be ordered and attributable to specific workers/files.

**Acceptance Criteria**
- [ ] Each parallel worker logs with a **worker prefix** in the log message: `[worker-01/scene_xyz]` or `[GPU:0/file_abc.tif]`.
- [ ] Implement one of these ordered-logging strategies:
  - **Option A (recommended)**: Use a `logging.handlers.QueueHandler` + `QueueListener` pattern. Workers push log records into a thread-safe `queue.Queue`. A single listener thread drains the queue and writes records sequentially.
  - **Option B**: Workers collect logs in memory and flush them upon completion in order.
- [ ] Log output shows a clear chronological order of events, even when workers run in parallel.
- [ ] The pattern is implemented as a reusable utility in `src/marine_litter/parallel_logging.py`.
- [ ] Prediction logging example:
  ```
  [worker-01/GPU:0] Starting prediction on T33TUM_20260328T100559_prediction.tif
  [worker-02/GPU:1] Starting prediction on T33TUN_20260328T100559_prediction.tif
  [worker-01/GPU:0] Completed in 38.2s (GPU peak: 11.2 GB)
  [worker-02/GPU:1] Completed in 41.7s (GPU peak: 11.4 GB)
  ```
- [ ] Download/ordering logging example:
  ```
  [order-01] Placed order abc-123 for scene S2A_...
  [order-02] Placed order def-456 for scene S2B_...
  [order-01] Order abc-123 fulfilled after 12m 34s
  [order-02] Order def-456 fulfilled after 14m 12s
  ```

**Technical Notes**
- `logging.handlers.QueueHandler` (Python 3.12+) sends `LogRecord` objects to a queue; `logging.handlers.QueueListener` reads them and dispatches to actual handlers. This is the stdlib solution for thread/process-safe logging.
- For `ProcessPoolExecutor`, the queue must be `multiprocessing.Queue`, not `queue.Queue`.
- Alternative: use `concurrent.futures.as_completed()` and collect results + logs together.
- This task has a dependency on ML-031 (logging config) and ML-033 (multi-GPU workers).

---

### ML-036 · [P0 / Task] Consolidate parallelism settings into `MLSettings` with env var control

**Description**
The project currently has `ML_ORDER_WORKERS` and `ML_PREDICT_WORKERS` as the only parallelism controls. For the H100 VM deployment, more granular control is needed, and all parallelism settings must be configurable via environment variables.

**Acceptance Criteria**
- [ ] Add/consolidate these settings in `MLSettings`:
  | Setting                 | Type  | Default | Description                                           |
  |-------------------------|-------|---------|-------------------------------------------------------|
  | `ML_ORDER_WORKERS`      | `int` | `3`     | Max parallel UP42 order placement + polling tasks      |
  | `ML_DOWNLOAD_WORKERS`   | `int` | `3`     | Max parallel asset downloads from UP42 STAC            |
  | `ML_PREDICT_WORKERS`    | `int` | `1`     | Max parallel prediction workers (1 per GPU ideally)    |
  | `ML_ZIP_WORKERS`        | `int` | `2`     | Max parallel zip→tif processing workers                |
  | `ML_UPLOAD_WORKERS`     | `int` | `2`     | Max parallel GCS uploads                               |
  | `ML_MAX_WORKERS_TOTAL`  | `int` | `0`     | Global cap (0 = no cap; sum of individual limits)      |
- [ ] `.example.env` updated with all new settings.
- [ ] `test_ml_settings.py` updated — `test_settings_defaults()` and `test_example_env_completeness()`.
- [ ] Each pipeline stage (download, zip, predict, upload) uses its corresponding worker setting.
- [ ] Validation: each worker count must be `≥ 1`.
- [ ] When `ML_DEVICE=cuda`, `ML_PREDICT_WORKERS` should not exceed `len(ML_GPU_IDS)` unless the user explicitly overrides (log a warning).
- [ ] Document all settings in `docker/readme.md`.

**Technical Notes**
- Currently `download_from_up42.py` uses `asyncio.gather` without a semaphore to limit concurrency. Add `asyncio.Semaphore(settings.order_workers)` to limit parallel orders.
- `predict_litter.py` uses `ThreadPoolExecutor(max_workers=settings.predict_workers)` — should switch to `ProcessPoolExecutor` for multi-GPU (see ML-033).
- `upload_to_gc_storage.py` currently uploads sequentially — parallelize with `ThreadPoolExecutor(max_workers=settings.upload_workers)`.
- The `ML_DOWNLOAD_WORKERS` setting is new — currently downloads happen inside the order polling loop one at a time.

---

### ML-037 · [P1 / Task] Add `--timing` flag for lightweight timing without full profiling

**Description**
Full profiling (ML-032) adds overhead. A lighter `--timing` flag should log just wall-clock time for each pipeline stage and per-file processing, without memory/GPU tracking.

**Acceptance Criteria**
- [ ] Add `--timing` / `-T` flag to all scripts.
- [ ] When active, log start/end/duration for:
  - Each pipeline stage (`download`, `process_zips`, `predict`, `upload`).
  - Each individual file operation (download, zip→tif, prediction, upload).
- [ ] Output format:
  ```
  [TIMING] Download: started at 10:00:00
  [TIMING]   scene_001.zip: 45.2s
  [TIMING]   scene_002.zip: 52.1s
  [TIMING] Download: completed in 97.3s (2 files)
  [TIMING] Prediction: started at 10:01:37
  [TIMING]   T33TUM_combined.tif: 38.2s
  [TIMING] Prediction: completed in 38.2s (1 file)
  [TIMING] Total pipeline: 142.8s
  ```
- [ ] `--timing` is independent of `--profile` (can be combined).
- [ ] Implementation reuses the `@profile_step` decorator from ML-032 with a lightweight mode.

**Technical Notes**
- Use `time.perf_counter()` for wall-clock (higher precision than `time.time()`).
- Minimal overhead — just two `perf_counter` calls per operation.
- This is the default recommendation for production cron jobs.

---

### ML-038 · [P1 / Refactor] Refactor pipeline into a `Pipeline` class with stage-based execution

**Description**
Currently `run_all.py` calls `download_from_up42.main()`, `predict_litter.main()`, and `upload_to_gc_storage.main()` sequentially with shared settings. This should be refactored into a proper `Pipeline` class that manages stages, settings, logging, profiling, and error handling in one place.

**Acceptance Criteria**
- [ ] Create `src/marine_litter/pipeline.py` with a `Pipeline` class:
  ```python
  class Pipeline:
      def __init__(self, settings: MLSettings, dry_run=False, profile=False, timing=False):
          ...
      def run(self, stages: list[str] | None = None):
          """Run all or selected stages: 'download', 'process', 'predict', 'upload'."""
          ...
  ```
- [ ] Each stage is a method: `_stage_download()`, `_stage_process_zips()`, `_stage_predict()`, `_stage_upload()`.
- [ ] Stages can be selectively run via CLI: `run_all.py --stages download,predict` (skip upload).
- [ ] The pipeline handles errors per-stage: if download fails, log the error and continue to predict on existing files.
- [ ] Profiling/timing is integrated at the pipeline level.
- [ ] `run_all.py` becomes a thin CLI wrapper that constructs and runs the `Pipeline`.
- [ ] The `Pipeline` class is importable and usable programmatically (e.g., from tests or Jupyter).

**Technical Notes**
- This enables better testability — each stage can be tested independently via the `Pipeline` class.
- Consider a `PipelineResult` dataclass that collects per-stage results, timing, errors.
- Depends on ML-010 (move logic to `src/`), ML-031 (logging), ML-032 (profiling).

---

### ML-039 · [P1 / Task] Add NVIDIA GPU health check and VRAM guard before prediction

**Description**
On the H100 VM, predictions should not start if a GPU is unhealthy or out of memory. Add pre-flight checks.

**Acceptance Criteria**
- [ ] Before prediction, check each configured GPU:
  - Is the GPU responsive? (`torch.cuda.get_device_properties(i)`).
  - Is there sufficient free VRAM? (configurable threshold, default: 4 GB via `ML_GPU_MIN_FREE_MB=4096`).
  - Is the GPU temperature within safe range? (via `nvidia-smi` parsing or `pynvml`, threshold: 85°C).
- [ ] If a GPU fails the health check:
  - Log a warning with details.
  - Exclude it from the worker pool (don't assign predictions to it).
  - If **all** GPUs fail, fall back to CPU with a prominent warning or abort (configurable via `ML_GPU_FALLBACK=cpu|abort`, default: `abort`).
- [ ] Add `ML_GPU_MIN_FREE_MB` and `ML_GPU_FALLBACK` to `MLSettings`.
- [ ] Health check results are logged at startup.

**Technical Notes**
- `torch.cuda.mem_get_info(device)` returns `(free, total)` in bytes — available since PyTorch 1.10.
- For temperature: `pynvml` (bundled with `nvidia-ml-py3`) or shell out to `nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits`.
- Keep `pynvml` optional — if not installed, skip temperature check and log a note.

---

### ML-040 · [P2 / Task] Add Docker healthcheck and resource limits

**Description**
For production deployment on the VM, the Docker container should have a healthcheck and configurable resource limits.

**Acceptance Criteria**
- [ ] Add `HEALTHCHECK` to `Dockerfile`:
  ```dockerfile
  HEALTHCHECK --interval=5m --timeout=10s --retries=3 \
    CMD python -c "import torch; import marine_litter" || exit 1
  ```
- [ ] `docker-compose.gpu.yml` adds GPU resource reservations and memory limits:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 64G
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
  ```
- [ ] Document recommended resource settings for different deployment scenarios:
  - H100 VM (4 GPUs, 256 GB RAM): `memory: 128G`, all GPUs.
  - Local dev (1 GPU, 16 GB RAM): `memory: 12G`, 1 GPU.
  - CPU-only: `memory: 8G`, no GPU.

**Technical Notes**
- Docker memory limits prevent OOM from killing the host.
- `--shm-size=2g` may be needed for PyTorch DataLoader workers (if used).

---

### ML-041 · [P2 / Task] Structured pipeline run summary — output a machine-readable report

**Description**
After each pipeline run, emit a structured JSON summary that can be consumed by monitoring tools, dashboards, or alerting systems.

**Acceptance Criteria**
- [ ] At the end of `run_all.py` (or `Pipeline.run()`), write a JSON summary to `ML_RUN_REPORT_PATH` (default: `_temp/run_report.json`).
- [ ] Report contents:
  ```json
  {
    "run_id": "uuid-v4",
    "started_at": "2026-03-31T10:00:00Z",
    "completed_at": "2026-03-31T10:19:23Z",
    "duration_seconds": 1163,
    "status": "success",
    "settings": { "device": "cuda", "predict_workers": 4, "gpu_ids": [0,1,2,3] },
    "stages": {
      "download": { "status": "success", "duration_s": 912, "files": 5 },
      "process_zips": { "status": "success", "duration_s": 24, "files": 5 },
      "predict": { "status": "success", "duration_s": 187, "files": 5 },
      "upload": { "status": "success", "duration_s": 34, "files": 5 }
    },
    "errors": [],
    "gpu_info": [
      { "id": 0, "name": "NVIDIA H100 80GB HBM3", "vram_mb": 81920, "peak_usage_mb": 11200 }
    ]
  }
  ```
- [ ] Add `ML_RUN_REPORT_PATH` to `MLSettings`.
- [ ] If `--profile` is active, include per-file timing in the report.

**Technical Notes**
- `uuid.uuid4()` for `run_id`.
- This enables building a monitoring dashboard or alerting on pipeline failures.

---

### ML-042 · [P2 / Docs] Document deployment scenarios — local dev, single GPU, multi-GPU H100 VM

**Description**
Document three deployment scenarios with recommended settings, Docker commands, and expected performance characteristics.

**Acceptance Criteria**
- [ ] Add `docs/deployment.md` with three sections:
  1. **Local Development (CPU-only)**:
     - Docker setup without GPUs.
     - Recommended settings: `ML_DEVICE=cpu`, `ML_PREDICT_WORKERS=1`.
     - Expected performance: ~10 min per TIF prediction.
  2. **Single GPU Workstation**:
     - Docker setup with `--gpus=1`.
     - Recommended settings: `ML_DEVICE=cuda`, `ML_GPU_IDS=0`, `ML_PREDICT_WORKERS=1`.
     - Expected performance: ~30s per TIF prediction.
  3. **Production VM (Multi-GPU H100)**:
     - Docker setup with `--gpus=all`.
     - Recommended settings: `ML_DEVICE=cuda`, `ML_GPU_IDS=0,1,2,3`, `ML_PREDICT_WORKERS=4`, `ML_ORDER_WORKERS=10`.
     - Expected performance: ~8s per TIF (4 in parallel).
     - Cron job setup, log rotation, monitoring.
- [ ] Include a quick-start command for each scenario.
- [ ] Link from `README.md` and `docker/readme.md`.
- [ ] Add mkdocs nav entry.

**Technical Notes**
- Performance estimates are rough — actual numbers should be measured and updated after initial deployment.
- H100 FP16 throughput is ~1979 TFLOPS — the UNet++ model should be very fast.

---

## Epic 7 — Code Audit: Bugs & Refactoring

### ML-043 · [P0 / Bug] `zip_processing.py` — TILE_ID XML tag detection has off-by-one logic error

**Description**
`src/marine_litter/zip_processing.py` lines 32–34:
```python
start_index = metadata_content.find(start_tag) + len(start_tag)
end_index = metadata_content.find(end_tag, start_index)
if start_index == -1 or end_index == -1:
    raise ValueError(...)
```
If `find(start_tag)` returns `-1` (tag not found), then `start_index = -1 + len(start_tag) = 29`, **not** `-1`. The guard `start_index == -1` is therefore **never True** when the tag is missing — it silently extracts garbage from the wrong position.

The existing test `test_process_zip_error_tile_id` passes only because the metadata content `<root><OTHER_TAG>value</OTHER_TAG></root>` happens to make `end_index == -1`, which catches the error. But if the metadata coincidentally contains `</TILE_ID>` somewhere else, the bug would produce wrong tile IDs silently.

**Acceptance Criteria**
- [x] Fix by checking `find()` result **before** adding `len(start_tag)`. *(done: `zip_processing.py:32-38`)*
- [x] Add a test with metadata that has `</TILE_ID>` but no opening tag. *(done: `test_process_zip_error_closing_tile_id_without_opening`)*
- [x] Add a test with completely unrelated XML content. *(done: `test_process_zip_error_unrelated_xml`)*

**Technical Notes**
- This is a classic off-by-one from doing arithmetic on a sentinel value (`-1`).
- Also see ML-051 for replacing string parsing with a proper XML parser.

---

### ML-044 · [P0 / Bug] `download_from_up42.py` — `order.status != "FAILED"` should be `"FAILED_PERMANENTLY"`

**Description**
`scripts/download_from_up42.py` line 179:
```python
while not order.is_fulfilled and order.status != "FAILED":
```
In **up42-py v3.4.0**, the `OrderStatus` type has `"FAILED_PERMANENTLY"`, not `"FAILED"`. The literal `"FAILED"` never matches any valid status, so the while-loop will never exit on a permanently-failed order — it will poll until the timeout.

Similarly, line 188:
```python
if timed_out or order.status == "FAILED":
```
This also never matches, so a failed order always looks like a timeout.

**Acceptance Criteria**
- [x] Change `"FAILED"` to `"FAILED_PERMANENTLY"` in both places. *(done: `download_from_up42.py:183,191` — uses `ORDER_TERMINAL_FAILURE_STATES` frozenset)*
- [x] Also handle `"CANCELED"` status (another terminal state in v3.4.0). *(done: included in `ORDER_TERMINAL_FAILURE_STATES`)*
- [x] Add constants or import `OrderStatus` types to avoid magic strings. *(done: `ORDER_TERMINAL_FAILURE_STATES` constant at line 51)*
- [x] Add a test that verifies failed order detection. *(done: `test_download_from_up42.py::TestOrderTerminalFailureStates` — 10 tests)*

**Technical Notes**
- v3.4.0 `OrderStatus` values: `CREATED`, `BEING_PLACED`, `PLACED`, `BEING_FULFILLED`, `FULFILLED`, `FAILED_PERMANENTLY`, `CANCELED`, `PLACEMENT_FAILED`.
- `Order.track()` already handles these correctly — once ML-005 is done, this bug is implicitly fixed, but it should be fixed independently too in case `track()` migration is deferred.

---

### ML-045 · [P0 / Bug] `download_from_up42.py` — `scene.cloud_coverage:5.1f` crashes when `cloud_coverage` is `None`

**Description**
`scripts/download_from_up42.py` line 151:
```python
log_lines.append(f"    {time_str} '{scene.id}':{scene.cloud_coverage:5.1f}% clouds")
```
`Scene.cloud_coverage` is typed as `float | None` in UP42 v3.4.0. When it is `None`, the format spec `:5.1f` raises `TypeError: unsupported format character`.

**Acceptance Criteria**
- [x] Guard against `None`. *(done: `download_from_up42.py:151-152`)*
- [x] Add a unit test with a scene that has `cloud_coverage=None`. *(done: `test_download_from_up42.py::TestCloudCoverageFormatting` — 5 tests)*

**Technical Notes**
- `Scene.cloud_coverage` comes from `properties.get("cloudCoverage")` which returns `None` for SAR or some non-optical data products.

---

### ML-046 · [P1 / Bug] `download_from_up42.py` — `assert` used for production error handling

**Description**
`scripts/download_from_up42.py` line 215:
```python
assert len(order_by_scene_id) == len(results)
```
`assert` statements are stripped when Python runs with `-O` (optimize) flag. Using `assert` for runtime validation in production code is an anti-pattern — it should use an explicit `if` + `raise`.

**Acceptance Criteria**
- [x] Replace with `if` + `log.error`. *(done: `download_from_up42.py:219-220`)*
- [x] ~~Or remove entirely~~ — kept as a defensive guard with `log.error` instead of `assert`.

**Technical Notes**
- `asyncio.gather` with `return_exceptions=True` always returns exactly one result per input coroutine. The assert is technically redundant but guards against a coding error. Logging the inconsistency is better than asserting.

---

### ML-047 · [P1 / Bug] `tif_processing.py` — GDAL dataset not explicitly closed in `get_tiff_layout()`

**Description**
`src/marine_litter/tif_processing.py` line 60:
```python
def get_tiff_layout(tiff: Path) -> dict:
    ds: Dataset = gdal.Open(str(tiff))
    band = ds.GetRasterBand(1)
    ...
    return {...}
```
The GDAL `Dataset` object `ds` is never explicitly closed. In CPython, the reference-counted GC usually closes it when the function returns, but:
1. If an exception occurs between `Open` and `return`, the file handle leaks.
2. In multi-threaded/process contexts (ML-033), leaked GDAL handles can cause `PermissionError` on Windows and resource exhaustion on Linux.
3. The CPython GC behaviour is an implementation detail, not guaranteed.

**Acceptance Criteria**
- [x] Explicitly close the dataset: `ds = None` at the end or wrap in a context manager. *(done: `band = None; ds = None` in `tif_processing.py:71-72`)*
- [x] Add error handling for `gdal.Open` returning `None` (file not found / corrupt): *(done: `tif_processing.py:61-62`)*
  ```python
  ds = gdal.Open(str(tiff))
  if ds is None:
      raise FileNotFoundError(f"GDAL could not open '{tiff}'")
  ```
- [x] Consider the same for `gdal.BuildVRT` and `gdal.Translate` in `zip_processing.py`. *(done: null checks + `FlushCache()` + explicit close for both)*

**Technical Notes**
- GDAL Python bindings don't support `with` statements. The convention is `ds = None` to trigger the destructor.
- `gdal.Open` returns `None` on failure (does not raise).

---

### ML-048 · [P0 / Bug] `zip_processing.py` — ZipSlip path traversal vulnerability in `extractall()`

**Description**
`src/marine_litter/zip_processing.py` line 17:
```python
zip_ref.extractall(extract_dir)
```
`zipfile.ZipFile.extractall()` is vulnerable to **ZipSlip** attacks — a malicious ZIP containing entries like `../../etc/passwd` can write files outside the target directory. While the project currently only processes ZIP files downloaded from UP42 (a trusted source), this is a critical security best practice.

**Acceptance Criteria**
- [x] Add path traversal validation before extraction. *(done: `zip_processing.py:17-20` — validates each member with `is_relative_to()`)*
- [x] Add a test with a crafted ZIP containing a `../` path. *(done: `test_process_zip_error_zipslip`)*

**Technical Notes**
- Python 3.12+ `zipfile` module has improved protections, but explicit validation is still recommended.
- `Path.is_relative_to()` is available since Python 3.9.

---

### ML-049 · [P1 / Bug] `Dockerfile` — model checkpoint downloaded over insecure HTTP

**Description**
`docker/Dockerfile` line 29:
```dockerfile
wget --no-check-certificate "http://dalic.de/mi4people/${MODEL_CKPT}"
```
The model checkpoint is downloaded over **plain HTTP** with `--no-check-certificate`, which is vulnerable to:
1. **Man-in-the-middle attacks** — an attacker could inject a malicious model file.
2. **Supply chain attacks** — the downloaded weights are loaded by `torch.load()`.

**Acceptance Criteria**
- [x] Switch to HTTPS: `https://dalic.de/mi4people/${MODEL_CKPT}`. *(done: `Dockerfile:29`)*
- [x] Remove `--no-check-certificate`. *(done: `Dockerfile:29`)*
- [ ] If HTTPS is not available, add a checksum verification step. *(N/A — HTTPS is used)*
- [ ] Document the model provenance and expected checksum in `docker/readme.md`. *(deferred — not blocking)*

**Technical Notes**
- The checkpoint is loaded with `torch.load(checkpoint_path, weights_only=True)` — `weights_only=True` mitigates some deserialization attacks, but a tampered weights file can still produce malicious model outputs.
- Consider hosting the checkpoint on a trusted CDN or GitHub Releases.

---

### ML-050 · [P1 / Bug] `predict_litter.py` — `shutil.rmtree(output_path)` silently destroys previous predictions

**Description**
`scripts/predict_litter.py` lines 103–104:
```python
if output_path.exists():
    shutil.rmtree(output_path)
    log.info(f"Cleared existing output directory: '{output_path}'")
```
This unconditionally deletes **all** content in the output directory before every run. If a user accidentally points `ML_OUTPUT_PATH` to a directory with important data, it's destroyed without confirmation.

**Acceptance Criteria**
- [ ] Only delete `*_prediction.tif` files from the output directory, not the entire directory tree.
- [ ] Or add a `--force-clean` flag that must be explicitly passed to enable `rmtree`.
- [ ] Log a warning before deletion listing what will be removed.
- [ ] Add a safety check: refuse to delete if `output_path` is `/`, `~`, or a parent of `src/`.

**Technical Notes**
- The `run_all.py` script calls `predict_litter.main()` which triggers this deletion on every automated run.
- Consider appending a timestamp subfolder instead: `output_path / "2026-03-31"`.

---

### ML-051 · [P1 / Refactor] `zip_processing.py` — replace string `find()` XML parsing with `xml.etree.ElementTree`

**Description**
`src/marine_litter/zip_processing.py` lines 29–35 parse XML using raw string `find()`:
```python
start_tag = '<TILE_ID metadataLevel="Brief">'
start_index = metadata_content.find(start_tag) + len(start_tag)
end_index = metadata_content.find(end_tag, start_index)
```
This is fragile — it breaks if:
1. The attribute order changes: `<TILE_ID metadataLevel="Brief">` vs `<TILE_ID   metadataLevel="Brief">`.
2. The XML has namespaces.
3. Whitespace differs between UP42 API versions.

**Acceptance Criteria**
- [ ] Replace with `xml.etree.ElementTree`:
  ```python
  import xml.etree.ElementTree as ET
  tree = ET.parse(metadata_file)
  tile_id_elem = tree.find('.//TILE_ID[@metadataLevel="Brief"]')
  if tile_id_elem is None or not tile_id_elem.text:
      raise ValueError(f"Tag TILE_ID not found in '{metadata_file.name}'")
  tile_id = tile_id_elem.text.strip()
  ```
- [ ] Update existing tests to match.
- [ ] No new dependencies (ElementTree is stdlib).

**Technical Notes**
- `xml.etree.ElementTree` handles attribute order, whitespace, and namespace prefixes automatically.
- Also fixes ML-043 (the off-by-one bug in `find()`) as a side effect.

---

### ML-052 · [P1 / Refactor] `run_all.py` — fragile `os.chdir()` + bare script imports

**Description**
`scripts/run_all.py` line 45:
```python
os.chdir(Path(__file__).resolve().parents[1])
```
And lines 6–8:
```python
import download_from_up42
import predict_litter
import upload_to_gc_storage
```
This pattern has multiple problems:
1. `os.chdir()` changes the working directory for the **entire process** globally — any other thread or async task is affected.
2. The bare imports only work because `os.chdir` puts the project root in the implicit path, and `scripts/` is in `sys.path` (or the CWD). This is invisible and fragile.
3. Every script (`download_from_up42.py`, `predict_litter.py`, `upload_to_gc_storage.py`) also has its own `os.chdir()` in `__main__` — if any of them is loaded as a module, the chdir doesn't fire, but code assumes relative paths.

**Acceptance Criteria**
- [ ] Remove all `os.chdir()` calls from all scripts.
- [ ] Make all paths absolute by resolving them from `settings` (which already has the paths).
- [ ] After ML-010 is complete, `run_all.py` imports from `marine_litter` package, not bare scripts.
- [ ] As an interim fix, add `scripts/` to `sys.path` explicitly rather than relying on `os.chdir`.

**Technical Notes**
- `os.chdir()` is thread-unsafe and a common source of bugs in concurrent code.
- The `MLSettings` paths are all relative — they should be resolved against the project root at construction time, not rely on CWD.
- Depends partially on ML-010 (move logic to `src/`).

---

### ML-053 · [P2 / Refactor] `merge_tiles.py` — hardcoded parameters and inconsistent style

**Description**
`scripts/merge_tiles.py` has multiple code quality issues:
1. Module-level constants (`INPUT_PATTERN`, `TARGET_SRS`, `PIXEL_SIZE`, etc.) are hardcoded and not configurable via `MLSettings` or CLI args.
2. Uses `glob.glob` and `os.path` instead of `pathlib.Path` (inconsistent with the rest of the codebase).
3. Creates a `reproj/` directory in CWD without cleanup.
4. No `argparse` integration — no way to override parameters from the command line.
5. No logging integration with the project's logging config.

**Acceptance Criteria**
- [ ] Add `argparse` with parameters for `input_pattern`, `target_srs`, `pixel_size`, `output_tif`.
- [ ] Use `pathlib.Path` throughout (replace `glob.glob`, `os.path.join`, `os.path.basename`).
- [ ] Add cleanup of the `reproj/` temp directory after VRT creation.
- [ ] Use `TemporaryDirectory` for the `reproj/` directory.
- [ ] Add `MLSettings` integration or document that this is a standalone utility.
- [ ] Add logging configuration matching other scripts.

**Technical Notes**
- This script is used for post-processing (merging prediction tiles) and is somewhat standalone.
- `PIXEL_SIZE = 0.0000898315` (~10m at the equator) — this should be documented.

---

### ML-054 · [P2 / Refactor] `ml_settings.py` — `__init__` string stripping is fragile

**Description**
`src/marine_litter/ml_settings.py` lines 80–83:
```python
for field_name, field_info in self.model_fields.items():
    if field_info.annotation is str:
        setattr(self, field_name, getattr(self, field_name).strip("\"' \t"))
```
Issues:
1. `field_info.annotation is str` uses identity check (`is`), not `isinstance`. If the annotation is `Optional[str]` or `str | None` in the future, this check fails silently.
2. `setattr` on a potentially frozen/validated Pydantic model can bypass validation.
3. Stripping quotes from values masks improperly formatted `.env` files — the user should fix their env file instead.

**Acceptance Criteria**
- [ ] Remove the stripping logic entirely. Pydantic and `python-dotenv` already handle quotes in `.env` files correctly.
- [ ] If stripping is truly needed, use a Pydantic `field_validator` instead:
  ```python
  @field_validator("*", mode="after")
  @classmethod
  def strip_strings(cls, v):
      return v.strip("\"' \t") if isinstance(v, str) else v
  ```
- [ ] Add a test that verifies quoted values in `.env` are handled correctly by Pydantic without stripping.

**Technical Notes**
- `python-dotenv` already strips quotes from `.env` values by default.
- A `field_validator("*")` with `mode="after"` runs on all fields after type coercion.

---

### ML-055 · [P2 / Refactor] `__init__.py` is empty — add package exports

**Description**
`src/marine_litter/__init__.py` is an empty file. The package has no explicit public API, making it unclear what should be imported.

**Acceptance Criteria**
- [ ] Add explicit imports and `__all__`:
  ```python
  from marine_litter.ml_settings import MLSettings
  from marine_litter.tif_processing import predict_litter, get_tiff_layout
  from marine_litter.zip_processing import process_zip
  
  __all__ = ["MLSettings", "predict_litter", "get_tiff_layout", "process_zip"]
  ```
- [ ] Add package-level `__version__` from `importlib.metadata`:
  ```python
  from importlib.metadata import version
  __version__ = version("marine-litter")
  ```
- [ ] Update imports in scripts to use the simplified public API.

**Technical Notes**
- This improves discoverability and enables `from marine_litter import MLSettings` directly.

---

### ML-056 · [P2 / Bug] `docker/run-analysis.sh` — hardcoded paths and missing `ML_` prefix

**Description**
`docker/run-analysis.sh`:
```bash
LOG_DIR="/home/demo1/logs"
docker run --rm -e DAYS_BEFORE=2 -e ORDER_WORKERS=3 -e PREDICT_WORKERS=3 -e DEVICE="cuda" marine_litter-image
```
Issues:
1. `LOG_DIR="/home/demo1/logs"` is hardcoded to a specific user's home directory.
2. Environment variables lack the `ML_` prefix (same issue as ML-014).
3. No `--gpus` flag for CUDA support.
4. Image name `marine_litter-image` doesn't match the `docker-compose.yml` service name.

**Acceptance Criteria**
- [ ] Use `ML_` prefixed env vars: `ML_DAYS_BEFORE`, `ML_ORDER_WORKERS`, etc.
- [ ] Use `${HOME}/logs` or a configurable `LOG_DIR` variable.
- [ ] Add `--gpus all` when `ML_DEVICE=cuda`.
- [ ] Match the image/container name with `docker-compose.yml`.
- [ ] Add `set -euo pipefail` for robust error handling.

**Technical Notes**
- This script is likely used for cron job deployment — correctness is critical.

---

### ML-057 · [P2 / Bug] `predict_litter.py` — `tif_file.unlink()` in cleanup deletes ALL TIFs, including non-prediction files

**Description**
`scripts/predict_litter.py` lines 40–43:
```python
# remove the litter prediction input TIFFs
for tif_file in input_path.glob("*.tif"):
    tif_file.unlink()
    log.debug(f"Deleted '{tif_file.name}'")
```
This deletes **all** `.tif` files in `input_path`, not just the combined TIFs created by `process_zip()`. If a user manually placed other TIF files in the input directory, they are silently destroyed.

Additionally, this runs **after** `move_predictions_and_remove_prediction_input_files()` which already moved `*_prediction.tif` files. So the remaining glob catches the combined input TIFs, which is the intent — but the `*.tif` glob is too broad.

**Acceptance Criteria**
- [ ] Narrow the glob to only match the expected filename pattern from `process_zip()`:
  ```python
  for tif_file in input_path.glob("T*_combined.tif"):
      tif_file.unlink()
  ```
  Or track which TIFs were created by `process_zip()` and delete only those.
- [ ] Log at `INFO` level (not `DEBUG`) when deleting files.
- [ ] Add a `--keep-inputs` flag to preserve input TIFs for debugging.

**Technical Notes**
- `process_zip()` creates files named `{tile_id}.tif` where `tile_id` comes from the metadata XML.
- The tile ID format is like `T33TUM_20260328T100559` — so the glob could be `T*.tif` for safety.

---

## Summary Table

| ID     | Priority | Type     | Title (short)                                          | Epic |
|--------|----------|----------|--------------------------------------------------------|------|
| ML-001 | P0       | Bug      | Auth migration — add `region`, handle `cfg_file`       | 1    |
| ML-002 | P0       | Bug      | Remove `MagicMock` — use `UP42_DISABLE_VERSION_CHECK`  | 1    |
| ML-003 | P0       | Bug      | Remove logger monkey-patch                             | 1    |
| ML-004 | P1       | Refactor | STAC download consistency with v3.4.0                  | 1    |
| ML-005 | P1       | Refactor | Use `Order.track()` instead of custom polling          | 1    |
| ML-006 | P1       | Task     | Verify `BatchOrderTemplate` estimate-on-construct      | 1    |
| ML-007 | P2       | Task     | Add `Order.cancel()` for stuck orders                  | 1    |
| ML-008 | P2       | Task     | Pin `up42-py~=3.4` in `pyproject.toml`                 | 1    |
| ML-009 | P0       | Bug      | `cpu_or_cuda.upper` → `.upper()` (missing parens)      | 2    |
| ML-010 | P1       | Refactor | Move UP42 logic from `scripts/` to `src/`              | 2    |
| ML-011 | P1       | Test     | Tests for `download_from_up42.py` (0% coverage)        | 2    |
| ML-012 | P1       | Test     | Tests for `predict_litter.py`                          | 2    |
| ML-013 | P1       | Test     | Tests for `upload_to_gc_storage.py`                    | 2    |
| ML-014 | P2       | Bug      | Docker-compose env vars missing `ML_` prefix           | 2    |
| ML-015 | P2       | Bug      | Docker-compose deprecated `version` key                | 2    |
| ML-016 | P2       | Refactor | Remove dead code in `upload_to_gc_storage.py`          | 2    |
| ML-017 | P2       | Refactor | Remove `unittest.mock` from production code            | 2    |
| ML-018 | P1       | Task     | Add `ML_REGION` setting for UP42 regions               | 3    |
| ML-019 | P2       | Task     | Add `--env-file` CLI argument to all scripts           | 3    |
| ML-020 | P2       | Task     | Clarify Dockerfile `COPY` paths                        | 3    |
| ML-021 | P3       | Task     | Add GitHub Actions CI pipeline                         | 3    |
| ML-022 | P1       | Docs     | Update Docker readme for current `MLSettings`          | 4    |
| ML-023 | P2       | Docs     | Fix Python version inconsistency in README             | 4    |
| ML-024 | P2       | Docs     | Document UP42 SDK dependency and version               | 4    |
| ML-025 | P3       | Docs     | Add architecture diagram                               | 4    |
| ML-026 | P3       | Task     | Deduplicate orders via `Order.all()`                   | 5    |
| ML-027 | P3       | Task     | Tag orders for traceability                            | 5    |
| ML-028 | P3       | Task     | Explore UP42 processing jobs                           | 5    |
| ML-029 | P3       | Task     | GEE prototype automation                               | 5    |
| ML-030 | P3       | Refactor | GEE JS `==` vs `=` bug fix                            | 5    |
| ML-031 | P0       | Task     | Configurable logging verbosity (simple/detailed/json)  | 6    |
| ML-032 | P0       | Task     | Per-process timing & resource profiling (`--profile`)  | 6    |
| ML-033 | P0       | Task     | Multi-GPU support — distribute across H100s            | 6    |
| ML-034 | P1       | Task     | Portable Docker — auto-detect CPU vs GPU               | 6    |
| ML-035 | P1       | Task     | Ordered logging in parallel workers (QueueHandler)     | 6    |
| ML-036 | P0       | Task     | Consolidate parallelism settings via env vars          | 6    |
| ML-037 | P1       | Task     | Lightweight `--timing` flag                            | 6    |
| ML-038 | P1       | Refactor | Refactor pipeline into `Pipeline` class                | 6    |
| ML-039 | P1       | Task     | GPU health check & VRAM guard before prediction        | 6    |
| ML-040 | P2       | Task     | Docker healthcheck & resource limits                   | 6    |
| ML-041 | P2       | Task     | Structured JSON pipeline run report                    | 6    |
| ML-042 | P2       | Docs     | Deployment scenarios (local/single-GPU/multi-GPU)      | 6    |
| ML-043 | P0       | Bug      | TILE_ID XML `find()` off-by-one logic error            | 7    |
| ML-044 | P0       | Bug      | `"FAILED"` should be `"FAILED_PERMANENTLY"` (v3.4.0)   | 7    |
| ML-045 | P0       | Bug      | `cloud_coverage:5.1f` crashes on `None`                | 7    |
| ML-046 | P1       | Bug      | `assert` used for production error handling            | 7    |
| ML-047 | P1       | Bug      | GDAL dataset not closed in `get_tiff_layout()`         | 7    |
| ML-048 | P0       | Bug      | ZipSlip path traversal vulnerability in `extractall()` | 7    |
| ML-049 | P1       | Bug      | Model checkpoint downloaded over insecure HTTP         | 7    |
| ML-050 | P1       | Bug      | `shutil.rmtree()` destroys previous predictions        | 7    |
| ML-051 | P1       | Refactor | Replace string `find()` XML with `ElementTree`         | 7    |
| ML-052 | P1       | Refactor | Remove fragile `os.chdir()` + bare script imports      | 7    |
| ML-053 | P2       | Refactor | `merge_tiles.py` hardcoded params & style              | 7    |
| ML-054 | P2       | Refactor | `MLSettings` string stripping is fragile               | 7    |
| ML-055 | P2       | Refactor | Empty `__init__.py` — add package exports              | 7    |
| ML-056 | P2       | Bug      | `run-analysis.sh` hardcoded paths & missing `ML_`      | 7    |
| ML-057 | P2       | Bug      | `tif_file.unlink()` deletes ALL TIFs, not just inputs  | 7    |
