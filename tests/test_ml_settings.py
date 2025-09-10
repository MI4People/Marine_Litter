from pathlib import Path

from src.marine_litter.ml_settings import MLSettings


def test_settings_defaults():
    settings = MLSettings()

    # Ensure all fields are tested
    tested_fields = {
        "log_level": "WARNING",
        "log_format": "%(asctime)s - %(levelname)s - %(message)s",
        # Paths
        "config_path": Path("resources/config.geojson"),
        "dates_path": Path("resources/dates.json"),
        "google_cred_path": Path("secrets/google_credentials.json"),
        "input_path": Path("images/downloaded"),
        "output_path": Path("images/predicted"),
        "up42_cred_path": Path("secrets/up42_credentials.json"),
        # Processing
        "bucket_name": "marinelitter_predicted",
        "days_before": 2,
        "product_id": "c3de9ed8-f6e5-4bb5-a157-f6430ba756da",
        "device": "cpu",
        "order_workers": 3,
        "predict_workers": 1,
    }
    missing_fields = set(MLSettings.model_fields.keys()) - set(tested_fields.keys())
    assert not missing_fields, f"Missing in test fields: {missing_fields}"
    extra_fields = set(tested_fields.keys()) - set(MLSettings.model_fields.keys())
    assert not extra_fields, f"Unwanted extra fields: {extra_fields}"

    # Test all field values
    for field_name, expected_value in tested_fields.items():
        actual_value = getattr(settings, field_name)
        assert actual_value == expected_value, f"Field '{field_name}': expected {expected_value}, got {actual_value}"


def test_settings_are_overridden_from_env_variables(a_test_env):
    settings = MLSettings(env_file=".example.env")

    # Logging
    assert settings.log_level == "ERROR"
    assert settings.log_format == "%(asctime)s - %(levelname)s - %(message)s"

    # Paths
    assert settings.config_path == Path("resources/config.geojson")
    assert settings.dates_path == Path("resources/dates.json")
    assert settings.google_cred_path == Path("secrets/google_credentials.json")
    assert settings.input_path == Path("images/downloaded")
    assert settings.output_path == Path("images/predicted")
    assert settings.up42_cred_path == Path("secrets/up42_credentials.json")

    # Processing settings
    assert settings.bucket_name == "a_bucket_name"
    assert settings.days_before == 3
    assert settings.product_id == "1234abcd-4321-cdef-fedc-1234567890ab"
    assert settings.device == "cuda"
    assert settings.order_workers == 2
    assert settings.predict_workers == 4
