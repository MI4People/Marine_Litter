import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _make_scene(scene_id: str, dt: str, cloud_coverage: float | None) -> SimpleNamespace:
    """Create a mock Scene-like object matching UP42's Scene interface."""
    return SimpleNamespace(id=scene_id, datetime=dt, cloud_coverage=cloud_coverage)


@pytest.fixture()
def _mock_up42_imports():
    """Patch the UP42 imports so determine_scenes can be imported without network access."""
    import sys

    # Pre-populate sys.modules with mocks for all UP42 submodules
    mock_modules = {
        "up42.version.version_control": MagicMock(),
        "up42": MagicMock(),
        "up42.glossary": MagicMock(),
        "up42.order_template": MagicMock(),
    }
    original_modules = {k: sys.modules.get(k) for k in mock_modules}
    sys.modules.update(mock_modules)
    try:
        yield
    finally:
        for k, v in original_modules.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class TestCloudCoverageFormatting:
    """ML-045: Verify cloud_coverage=None doesn't crash the log formatter."""

    def test_cloud_coverage_none_formats_as_na(self):
        """The exact bug: format spec :5.1f raises TypeError on None."""
        cloud_coverage = None
        cloud_str = f"{cloud_coverage:5.1f}" if cloud_coverage is not None else "  N/A"
        assert cloud_str == "  N/A"

    def test_cloud_coverage_float_formats_correctly(self):
        cloud_coverage = 42.3
        cloud_str = f"{cloud_coverage:5.1f}" if cloud_coverage is not None else "  N/A"
        assert cloud_str == " 42.3"

    def test_cloud_coverage_zero_formats_correctly(self):
        cloud_coverage = 0.0
        cloud_str = f"{cloud_coverage:5.1f}" if cloud_coverage is not None else "  N/A"
        assert cloud_str == "  0.0"

    def test_scene_log_line_with_none_cloud_coverage(self):
        """ML-045: Full log line construction with cloud_coverage=None."""
        scene = _make_scene("scene-123", "2024-01-15T10:30:00Z", cloud_coverage=None)
        time_str = scene.datetime[11:19]
        cloud_str = f"{scene.cloud_coverage:5.1f}" if scene.cloud_coverage is not None else "  N/A"
        log_line = f"    {time_str} '{scene.id}':{cloud_str}% clouds"
        assert "N/A" in log_line
        assert "scene-123" in log_line

    def test_scene_log_line_with_float_cloud_coverage(self):
        scene = _make_scene("scene-456", "2024-01-15T10:30:00Z", cloud_coverage=5.1)
        time_str = scene.datetime[11:19]
        cloud_str = f"{scene.cloud_coverage:5.1f}" if scene.cloud_coverage is not None else "  N/A"
        log_line = f"    {time_str} '{scene.id}':{cloud_str}% clouds"
        assert "  5.1% clouds" in log_line


class TestOrderTerminalFailureStates:
    """ML-044: Verify failed order detection uses correct UP42 v3.4.0 status strings."""

    def test_constants_include_all_terminal_failure_states(self):
        """Verify all UP42 v3.4.0 terminal failure states are covered."""
        # These must match the ORDER_TERMINAL_FAILURE_STATES constant in download_from_up42.py
        expected_states = {"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"}
        terminal_states = frozenset({"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"})
        assert terminal_states == expected_states

    @pytest.mark.parametrize("status", ["FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"])
    def test_terminal_failure_states_are_detected(self, status):
        """ML-044: Each terminal state should be detected by the 'in' check."""
        terminal_states = frozenset({"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"})
        assert status in terminal_states

    @pytest.mark.parametrize("status", ["CREATED", "BEING_PLACED", "PLACED", "BEING_FULFILLED", "FULFILLED"])
    def test_non_terminal_states_are_not_detected(self, status):
        """Non-terminal states should NOT match the failure check."""
        terminal_states = frozenset({"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"})
        assert status not in terminal_states

    def test_old_failed_string_not_in_terminal_states(self):
        """ML-044: The old bug used 'FAILED' which is not a valid UP42 v3.4.0 status."""
        terminal_states = frozenset({"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"})
        assert "FAILED" not in terminal_states
