"""Configuration management for marine litter detection package."""

import logging
from pathlib import Path

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

DFT_PRODUCT_ID = "1234abcd-4321-cdef-fedc-1234567890ab"
log = logging.getLogger(__name__)


class MLSettings(BaseSettings):
    """Configuration for marine litter detection with defaults.
    Latter can be overridden by environment variables with `ML_` prefix from OS or env file, like './.example.env'.

    Note, pydantic-settings loads the configuration in this order, overriding the previous one:
      - default values of the class
      - OS environment variables (with ML_ prefix here)
      - env file environment variables, when given like `env_file=".env"`
      - explicit parameters (passed to the constructor)
    See documentation https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """

    model_config = ConfigDict(extra="forbid")

    # (keep alphabetically per group, sync .env.example accordingly)

    # Logging
    log_level: str = Field(default="WARNING")
    log_format: str = Field(default="%(message)-100s |%(levelname).1s %(asctime)s %(filename)s:%(lineno)d")

    # Paths
    #   PyTorch caches checkpoints in '~/.cache/torch/hub/checkpoints' (default location),
    #       in Windows '%USERPROFILE%\.cache\torch\hub\checkpoints'.
    checkpoint_file: str = Field(default="", description="ckpt file for marinedebrisdetector predictor")
    checkpoints: Path = Field(default=Path("~/.cache/torch/hub/checkpoints"), description="folder with ckpt files")
    config_path: Path = Field(default=Path("resources/config.geojson"), description="GeoJSON file for UP42 downloads")
    dates_path: Path = Field(default=Path("resources/dates.json"), description="Predicted dates JSON file")
    input_path: Path = Field(default=Path("images/downloaded"), description="Downloaded images folder (zip/tif files)")
    output_path: Path = Field(default=Path("images/predicted"), description="Processed images folder (predictions)")
    #   Like '.env' file: Do not commit credentials to version control!
    google_creds_path: Path = Field(default=Path("secrets/google_credentials.json"), description="Google credentials")
    up42_creds_path: Path = Field(default=Path("secrets/up42_credentials.json"), description="UP42 credentials")

    # Processing
    bucket_name: str = Field(default="marinelitter_predicted", description="Google Cloud Storage bucket name")
    days_before: int = Field(default=2, description="Search for images at date back from today")
    device: str = Field(default="cpu", description="Options: cpu|cuda")
    order_workers: int = Field(default=3, description="Number of parallel workers for ordering (download)")
    predict_workers: int = Field(default=1, description="Number of parallel workers for prediction")
    product_id: str = Field(default=DFT_PRODUCT_ID, description="See `up42.Catalog.construct_order_parameters`")

    @field_validator(
        "checkpoints",
        "config_path",
        "dates_path",
        "input_path",
        "output_path",
        "google_creds_path",
        "up42_creds_path",
        mode="before",
    )
    @classmethod
    def expand_user_path(cls, v):
        """Expand ~ to user home directory for cross-platform compatibility (Windows/Linux)."""
        if isinstance(v, str):
            return Path(v).expanduser()
        else:
            return v.expanduser()

    def __init__(self, env_file: str | Path | None = None, **kwargs):
        if env_file and not Path(env_file).is_file():
            raise FileNotFoundError(str(env_file))
        super().__init__(_env_prefix="ML_", _env_file=str(env_file), _env_file_encoding="utf-8", **kwargs)

    def as_tuples(self):
        return [
            (k, v, type(self).model_fields[k].default, type(self).model_fields[k].description)
            for k, v in self.model_dump().items()
        ]

    def as_table(self, default=False, description=False) -> str:
        """Return settings as vertically aligned table, skipping latter 2 column when set to `False`."""
        rows = [("Name", "Value", "Default", "Description"), *self.as_tuples()]
        cols = [0, 1] + ([2] if default else []) + ([3] if description else [])
        widths = [max(len(str(r[i])) for r in rows) for i in cols]
        return "\n".join(" | ".join(str(row[i]).ljust(w) for i, w in zip(cols, widths, strict=False)) for row in rows)
