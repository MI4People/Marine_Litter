# Marine Litter
A Python project for detecting marine litter via satellite imagery using artificial intelligence
(plus some GUI: JavaScript for Google Earth Engine).

> This page concentrates on development,
> for **project overview, technical details, and usage**, see the [**Documentation**](docs/index.md).

## Development Setup

### Prerequisites
- Python ≥3.11
- [`uv`](https://github.com/astral-sh/uv) package and project manager
- [`ruff`](https://github.com/astral-sh/ruff) for formatting and linting,
  it also calls [isort](https://github.com/PyCQA/isort) and [black](https://github.com/psf/black).

Install these like
- Windows: `winget install -e astral-sh.uv astral-sh.ruff`
- macOS: `brew install uv ruff`
- Linux: `sudo apt install pipx && pipx install uv ruff`

### Quick Start
Prerequisites: You need `c++`and `gdal-devel` + `gdal-config` with version number matching the gdal version in the `pyproject.toml` installed on your system.
Simplest approach is to use system gdal (e.g., `sudo apt install -y python3-gdal` on Linux). See [https://gdal.org/en/stable/download.html] for more details on installing gdal.

For development, Python should be used in a [venv](https://docs.python.org/3/library/venv.html).
This is done by `uv` automatically into project root `.venv/`, when not called with `--active`.
```bash
# get dependencies including pytest etc.
uv sync
```

If you prefer to keep the `venv` outside of the project, and to avoid the need to prepend non-uv calls with `uv run `,
you can [create a `venv` manually and activate it](https://docs.python.org/3/tutorial/venv.html),
but need to add `--active` to `uv sync` calls then:
```bash
# get dependencies including pytest etc.
uv sync --active
```

Then you could use the Python scripts in 'scripts/', or run `pytest`,
but you might want to understand the repo structure and configurations first...

### Repository Structure
~~~
/docker/       - Docker related files, including readme for setup
./docs/         - for documentation via https://www.mkdocs.org/
./resources/    - GIS configuration etc.
./scripts/      - to run for analysis
./secrets/      - (git-ignored) credentials
./specs/        - feature specifications
./src/          - actual package code
./testdata/     - small sample data for pytest
./tests/        - for pytest
./web_gee/      - frontend: JavaScript for Google Earth Engine
~~~

Some temporary (git-ignored) directories like `_temp/`, or `site/` may be produced by certain tools or scripts.

The ['pyproject.toml'](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) in the project root
is used by the mentioned above tools `uv`, `ruff`, or installed then `dev` dependencies, like
[`pytest`](https://docs.pytest.org/), or [`mkdocs`](https://www.mkdocs.org/).

Note the subtle **naming** differences between
- project name 'Marine Litter'
- git repo name 'Marine_Litter'
- Python package name 'marine-litter', and
- module name `marine_litter`.

### Configuration of the Python scripts
The project uses [Pydantic Settings](https://github.com/pydantic/pydantic-settings) for configuration.
You should copy '.example.env' to a parallel **'.env'** (which should stay excluded by '.gitignore'),
and adjust the values as needed, see als 'src/marine_litter/ml_settings.py', or 'tests/test_ml_settings.py'.

_When 'ml_settings.py' evolves, also update '.example.env' and tests accordingly._

## Development and Analysis

### Git
We use a specific **branch naming convention** to maintain clarity (with date for creation)
- `feature/<featurename>_<YYYYMMDD>`
- `bugfix/<bugname>_<YYYYMMDD>`

### Using `uv`, `ruff`, and `pytest` (Quality Checks)
While developing, please regularly run the following commands.

_Adapt parameters, like omitting `--active` when using local '.venv/',
see [uv documentation](https://docs.astral.sh/uv/concepts/projects/sync) for details_

Ensure all these are fine **_before_ committing** a change to git.
```bash
# update dependencies (including `dev` ones), updates `uv.lock`
uv sync --active --upgrade

# check code and fix linting issues
ty check --output-format concise
ruff check --preview --fix --unsafe-fixes

# run all tests
pytest tests
```

### Docker
See the extra [**Docker readme**](docker/readme.md), namely you could test the built Docker image by
```bash
docker run --rm --env-file .env -v ./secrets:/marine_litter/secrets:ro marine_litter python scripts/run_all.py --dry-run
```

### Frontend Development (JavaScript for Google Earth Engine)
> **TBD**

### Analysis and Other Scripts
You may want to run the complete pipeline, or parts of it like below.
Depending on your OS and having
- 'scripts/' in `PATH`
- a venv active, or
- parameters to add

adapt how you call the all-in-one or single scripts:
```bash
run_all.py
scripts\run_all.py
uv run scripts/run_all.py
uv run --active scripts/run_all.py
```

#### Viewing tiles ('scripts/vizualize_tile.py')
For visual inspection of downloaded GeoTIFFs, this renders a band combination via `gdal_translate`
and shows it in a resizable window. Pass a single '.tif', or a folder of them:
```bash
uv run scripts/vizualize_tile.py resources/download_images/
```
- `left` / `right` – previous / next file in the folder
- `up` / `down` – previous / next band combination (true colour, false colour infrared, SWIR)
- `q` or `escape` – quit

Band combinations are defined in `COMBOS` at the top of the script, using band positions in the
order that 'src/marine_litter/zip_processing.py' merges them (B11 and B12 end up on 10 and 11,
B8A last on 12).

It needs `opencv-python` from the `dev` group — the *headless* build has no window support — plus
the X11 and OpenGL libraries it links against. The devcontainer image installs those already
(see '.devcontainer/Dockerfile'), on another Linux machine call
```bash
sudo apt install -y libgl1 libglib2.0-0 libsm6 libxcb1 libxext6 libxkbcommon-x11-0 libxrender1
```

It also needs a **reachable display**. VS Code forwards the host's X socket into the devcontainer
(it is listed in `REMOTE_CONTAINERS_SOCKETS`) and sets `DISPLAY`, but it does *not* forward the
authorisation cookie for it. The host X server then refuses the connection, and Qt reacts to that
by aborting the process. The script checks the display up front and reports this instead, the fix
is to permit local clients from a terminal *on the host*:
```bash
xhost +local:
```
Should that not work for your host session, run the script on the host rather than in the container.

#### Land masking ('src/marine_litter/landmask.py')
Before prediction, land is masked in every tile, so marine litter is only detected on water
(see the [**spec**](specs/landmask.md) for details and design decisions):
- Once per run, the IHO Sea Areas around the AOI ('resources/features.geojson') are fetched from the
  [Marine Regions](https://www.marineregions.org) WFS, and stored in `ML_LANDMASK_PATH`
  ('resources/landmask.geojson', git-ignored). Without network, that local copy is used, and without both,
  the run predicts unmasked with a warning.
- Per tile, land pixels (sea areas grown inland by `ML_LANDMASK_BUFFER_M`, as the IHO coastline is coarse)
  are filled with the median of the tile's water pixels, a water-like neutral value.
  Tiles without water are skipped, and the prediction is set to 0 on land.
- Switch it off with `ML_LANDMASK_ENABLED=false`.

For visual checks on a single tile, see 'src/LandMask.ipynb' and 'src/landmask_validation.py'.


### CVE-2025-63396 (PyTorch Profiler Bug)
- **Status**: CVSS 3.3 LOW - Not a security vulnerability
- **Affected**: PyTorch 2.5, 2.7.1, 2.9.1 (likely)
- **Issue**: Forgetting `profiler.stop()` causes crashes/hangs in `torch.profiler.profile`
- **References**:
    - [NVD CVE Details](https://nvd.nist.gov/vuln/detail/CVE-2025-63396)
    - [PyTorch GitHub Issue](https://github.com/pytorch/pytorch/issues/156563)
    - [PyTorch Security Advisories](https://github.com/pytorch/pytorch/security/advisories)

#### Why not a security issue?
- Requires user error (API misuse)
- Only affects developer's own code
- Cannot be exploited for attacks

#### Recommendation
- **Safe to ignore**, if using the profiler, call `.stop()` properly
- Watch for future PyTorch releases addressing this.

## Documentation
We use [MkDocs](https://www.mkdocs.org/) for documentation,
and [Read the Docs](https://readthedocs.com/) to publish it.

### MkDocs
To improve the documentation, add or edit the Markdown files in 'docs/' and create a pull request.

The standard usage to test changes is to start a local documentation server, which nicely auto-reloads on changes
(adapt the port if needed):
```bash
mkdocs serve -a 127.0.0.1:8001
```
You could also create, or update a documentation 'site/' (git-ignored) by calling `mkdocs build`.

### Read the Docs
To publish the documentation, Read the Docs needs 'docs/requirements.txt',
which is generated from the dependencies given in 'docs/requirements.in'.
- install `pip-tools` (see 'pyproject.toml' "dev" group, should be done by `uv sync` already)
    ```bash
    pip install -U pip-tools
    ```
- call
    ```bash
    pip-compile docs/requirements.in
    ```
- commit and push the generated `docs/requirements.txt`, if the "docs" dependencies change.

Note, these "docs" dependencies need to **keep in sync** in
- 'docs/requirements.in' and
- 'pyproject.toml',

like to **test the Documentation** via `mkdocs serve` before pushing.

## License, Issues and Contributing
This project is licensed under the **MIT License**, see [LICENSE.txt](LICENSE.txt).

Report bugs or request features via project's **issues**: https://github.com/MI4People/Marine_Litter/issues.

**Contributing**
- Fork the repository
- Create a branch as written above under **Git**
- Follow the coding and quality guidelines from above
- Note your changes in the [**CHANGELOG.md**](CHANGELOG.md), and update the version in 'pyproject.toml'
- Submit a pull request.
