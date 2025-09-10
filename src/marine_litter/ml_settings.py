"""Configuration management for marine litter detection package."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

DFT_PRODUCT_ID = "c3de9ed8-f6e5-4bb5-a157-f6430ba756da"


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
    # Logging
    log_level: str = Field(default="WARNING")
    log_format: str = Field(default="%(asctime)s - %(levelname)s - %(message)s")

    # Paths
    config_path: Path = Field(default=Path("resources/config.geojson"), description="GeoJSON config file")
    dates_path: Path = Field(default=Path("resources/dates.json"), description="Dates JSON file")
    google_cred_path: Path = Field(default=Path("secrets/google_credentials.json"))
    input_path: Path = Field(default=Path("images/downloaded"), description="Downloaded images folder")
    output_path: Path = Field(default=Path("images/predicted"), description="Processed images folder")
    up42_cred_path: Path = Field(default=Path("secrets/up42_credentials.json"))

    # Processing
    bucket_name: str = Field(default="marinelitter_predicted", description="Google Cloud Storage bucket name")
    days_before: int = Field(default=2, description="Number of days before current date to search")
    product_id: str = Field(default=DFT_PRODUCT_ID, description="for `up42.Catalog.construct_order_parameters`")
    device: str = Field(default="cpu", description="options: cpu|cuda")
    order_workers: int = Field(default=3, description="Number of parallel workers for ordering (download)")
    predict_workers: int = Field(default=1, description="Number of parallel workers for prediction")

    def __init__(self, env_file: str | None = None):
        super().__init__(_env_prefix="ML_", _env_file=env_file, _env_file_encoding="utf-8")
