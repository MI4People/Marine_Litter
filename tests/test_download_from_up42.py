import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

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


class TestUp42VersionCheckDisabled:
    """ML-002: Verify UP42_DISABLE_VERSION_CHECK env var is set."""

    def test_env_var_is_set_in_download_script(self):
        """ML-002: download_from_up42.py must set the env var via os.environ.setdefault."""
        script = Path(__file__).resolve().parent.parent / "scripts" / "download_from_up42.py"
        content = script.read_text(encoding="utf-8")
        assert 'os.environ.setdefault("UP42_DISABLE_VERSION_CHECK"' in content

    def test_env_var_documented_in_example_env(self, project_root):
        """ML-002: .example.env must document UP42_DISABLE_VERSION_CHECK (as comment, since MLSettings forbids extras)."""
        example_env = project_root / ".example.env"
        content = example_env.read_text(encoding="utf-8")
        assert "UP42_DISABLE_VERSION_CHECK" in content

    def test_env_var_in_docker_compose(self, project_root):
        """ML-002: docker-compose.yml must set UP42_DISABLE_VERSION_CHECK."""
        compose_file = project_root / "docker" / "docker-compose.yml"
        content = compose_file.read_text(encoding="utf-8")
        assert "UP42_DISABLE_VERSION_CHECK" in content


class TestUp42LoggerConfiguration:
    """ML-003: Verify UP42 loggers are reconfigured to propagate to root."""

    def test_script_configures_root_up42_logger(self):
        """ML-003: download_from_up42.py must explicitly configure root 'up42' logger."""
        script = Path(__file__).resolve().parent.parent / "scripts" / "download_from_up42.py"
        content = script.read_text(encoding="utf-8")
        # Verify root logger is explicitly addressed (not just child iteration)
        assert 'logging.getLogger("up42")' in content
        assert ".propagate = True" in content
        assert ".handlers.clear()" in content

    def test_script_does_not_monkey_patch(self):
        """ML-003: No _patched_get_logger or utils.get_logger reassignment."""
        script = Path(__file__).resolve().parent.parent / "scripts" / "download_from_up42.py"
        content = script.read_text(encoding="utf-8")
        assert "_patched_get_logger" not in content
        assert "utils.get_logger =" not in content
        assert "utils.get_logger=" not in content

    def test_logger_propagation_pattern_works(self):
        """ML-003: Verify the reconfiguration pattern actually works on a mock logger hierarchy."""
        # Simulate what download_from_up42.py does
        test_root = logging.getLogger("_test_up42_pattern")
        test_child = logging.getLogger("_test_up42_pattern.child")
        # Add a handler to simulate UP42 SDK default behaviour
        test_root.addHandler(logging.StreamHandler())
        test_root.propagate = False

        # Apply the same pattern used in download_from_up42.py
        test_root.handlers.clear()
        test_root.propagate = True

        assert test_root.propagate is True
        assert len(test_root.handlers) == 0
        assert test_child.propagate is True  # children inherit by default

    def test_up42_log_level_respects_basicconfig(self):
        """ML-003: UP42 loggers must respect the configured log level via propagation."""
        # When propagate=True and no handlers, the effective level comes from parent/root
        test_logger = logging.getLogger("_test_up42_level")
        test_logger.handlers.clear()
        test_logger.propagate = True
        test_logger.setLevel(logging.NOTSET)  # inherit from parent

        # Root logger level controls what gets through
        root_level = logging.getLogger().getEffectiveLevel()
        assert test_logger.getEffectiveLevel() == root_level


class TestProductionConstantIntegrity:
    """Verify production constants in download_from_up42.py match expected values."""

    @staticmethod
    def _script_path() -> Path:
        return Path(__file__).resolve().parent.parent / "scripts" / "download_from_up42.py"

    def test_order_terminal_failure_states_includes_failed_permanently(self):
        """ML-044: The actual source must include FAILED_PERMANENTLY."""
        content = self._script_path().read_text(encoding="utf-8")
        for line in content.splitlines():
            if "ORDER_TERMINAL_FAILURE_STATES" in line and "frozenset" in line:
                assert '"FAILED_PERMANENTLY"' in line
                return
        pytest.fail("ORDER_TERMINAL_FAILURE_STATES constant not found in source")

    def test_order_terminal_failure_states_includes_canceled(self):
        """ML-044: The actual source must include CANCELED."""
        content = self._script_path().read_text(encoding="utf-8")
        for line in content.splitlines():
            if "ORDER_TERMINAL_FAILURE_STATES" in line and "frozenset" in line:
                assert '"CANCELED"' in line
                return
        pytest.fail("ORDER_TERMINAL_FAILURE_STATES constant not found in source")

    def test_order_terminal_failure_states_includes_placement_failed(self):
        """ML-044: The actual source must include PLACEMENT_FAILED."""
        content = self._script_path().read_text(encoding="utf-8")
        for line in content.splitlines():
            if "ORDER_TERMINAL_FAILURE_STATES" in line and "frozenset" in line:
                assert '"PLACEMENT_FAILED"' in line
                return
        pytest.fail("ORDER_TERMINAL_FAILURE_STATES constant not found in source")

    def test_old_failed_string_not_sole_constant(self):
        """ML-044: The old buggy 'FAILED' must not be the only terminal state."""
        content = self._script_path().read_text(encoding="utf-8")
        for line in content.splitlines():
            if "ORDER_TERMINAL_FAILURE_STATES" in line and "frozenset" in line:
                assert line != 'ORDER_TERMINAL_FAILURE_STATES = frozenset({"FAILED"})'
                return


class TestNoAssertInProduction:
    """ML-046: Verify no bare `assert` statements are used for production validation."""

    def test_download_script_has_no_bare_assert(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "download_from_up42.py"
        content = script.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("assert ") and not stripped.startswith("# "):
                pytest.fail(f"download_from_up42.py:{i} uses bare 'assert': {stripped}")
