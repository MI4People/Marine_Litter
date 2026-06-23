import logging
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from marine_litter.ml_settings import MLSettings

log = logging.getLogger(__name__)


def test_settings_defaults() -> None:
    # Ensure all fields are tested (vs. `MLSettings` defaults)
    tested_fields = {
        "log_level": "WARNING",
        "log_format": "%(message)-100s |%(levelname).1s %(asctime)s %(filename)s:%(lineno)d",
        # Authentication
        "google_creds_path": Path("secrets/google_credentials.json"),
        "up42_creds_path": Path("secrets/up42_credentials.json"),
        # Paths
        "checkpoint_file": "",
        "checkpoints": Path("~/.cache/torch/hub/checkpoints").expanduser(),
        "dates_path": Path("resources/dates.json"),
        "geojson_path": Path("resources/features.geojson"),
        "input_path": Path("images/downloaded"),
        "output_path": Path("images/predicted"),
        # Processing
        "bucket_name": "marinelitter_predicted",
        "clouds_perc_max": 50,
        "days_before": 2,
        "days_num": 1,
        "device": "cpu",
        "order_workers": 3,
        "predict_workers": 1,
        "product_name": "sentinel-2-level-2a",
    }
    missing_fields = set(MLSettings.model_fields.keys()) - set(tested_fields.keys())
    assert not missing_fields, f"Missing in test fields: {missing_fields}"
    extra_fields = set(tested_fields.keys()) - set(MLSettings.model_fields.keys())
    assert not extra_fields, f"Unwanted extra fields: {extra_fields}"

    # Test all field values
    settings = MLSettings()
    for field_name, expected_value in tested_fields.items():
        actual_value = getattr(settings, field_name)
        assert actual_value == expected_value, f"Field '{field_name}': expected {expected_value}, got {actual_value}"


def test_example_env_completeness(env_file: Path) -> None:
    env_fields = []
    with open(env_file, "r", encoding="utf-8") as f:
        env_fields.extend(m[1].lower() for line in f.readlines() if (m := re.match("^ML_([A-Z0-9_]+) *=", line)))

    missing_fields = set(MLSettings.model_fields.keys()) - set(env_fields)
    assert not missing_fields, f"Missing in '.example.env' fields: {missing_fields}"


def test_missing_env_file_raises_file_not_found_error() -> None:
    with pytest.raises(FileNotFoundError):
        MLSettings(env_file="non_existent.env")


def test_single_args() -> None:
    for level_str in ["DEBUG", "INFO"]:
        settings = MLSettings(log_level=level_str)
        assert level_str == settings.log_level


def test_unknown_arguments_are_rejected() -> None:
    with pytest.raises(ValidationError) as e:
        MLSettings(unknown_field="some_value")
    assert "unknown_field" in str(e.value)


def test_as_table(caplog: pytest.LogCaptureFixture) -> None:
    table_output = MLSettings().as_table(description=True)
    assert re.search(r"Name +\| Value +\| Description", table_output)
    assert "    | Default" not in table_output


def test_settings_are_overridden_from_env_variables(env_file: Path) -> None:
    settings = MLSettings(env_file)

    # Logging
    assert settings.log_level == "INFO"
    assert settings.log_format == "%(message)-100s |%(levelname).3s %(asctime)s %(filename)s:%(lineno)d"

    # Authentication
    assert settings.google_creds_path == Path("secrets/google_credentials.json")
    assert settings.up42_creds_path == Path("secrets/up42_credentials.json")

    # Paths
    assert settings.checkpoint_file == "epoch=54-val_loss=0.50-auroc=0.987.ckpt"
    assert settings.checkpoints == Path("~/.cache/torch/hub/checkpoints").expanduser()
    assert settings.dates_path == Path("resources/dates.json")
    assert settings.geojson_path == Path("resources/features.geojson")
    assert settings.input_path == Path("images/downloaded")
    assert settings.output_path == Path("images/predicted")

    # Processing settings
    assert settings.bucket_name == "marinelitter_predicted"
    assert settings.clouds_perc_max == 42
    assert settings.days_before == 3
    assert settings.days_num == 1
    assert settings.device == "cuda"
    assert settings.order_workers == 2
    assert settings.predict_workers == 4


def test_settings_expands_os_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ML_INPUT_PATH", "~/test/input")
    settings = MLSettings()
    assert settings.input_path == Path("~/test/input").expanduser()
    assert not str(settings.input_path).startswith("~")
