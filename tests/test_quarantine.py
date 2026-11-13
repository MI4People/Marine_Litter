from pathlib import Path

from marine_litter import quarantine


def _tif(tmp_path: Path, name: str = "scene.tif") -> Path:
    f = tmp_path / name
    f.write_bytes(b"dummy")
    return f


def test_normal_run_leaves_no_marker(tmp_path: Path) -> None:
    tif = _tif(tmp_path)
    assert quarantine.check_and_mark(tif) is True
    quarantine.clear_in_progress(tif)  # what the `finally` in predict_litter does
    assert quarantine.check_and_mark(tif) is True  # next run: processed again normally, no quarantine
    assert not quarantine.quarantine_dir(tif).exists()


def test_crash_puts_file_into_quarantine(tmp_path: Path) -> None:
    tif = _tif(tmp_path)
    assert quarantine.check_and_mark(tif) is True
    # segfault: process dies, `finally` never runs, the marker stays

    assert quarantine.check_and_mark(tif) is False  # next run
    qdir = quarantine.quarantine_dir(tif)
    assert (qdir / "scene.tif").exists()
    assert (qdir / "scene.tif.txt").exists()
    assert not tif.exists()
    assert not quarantine.crashed_last_time(tif)


def test_quarantined_file_is_skipped_when_extracted_again(tmp_path: Path) -> None:
    tif = _tif(tmp_path)
    quarantine.check_and_mark(tif)
    quarantine.check_and_mark(tif)  # crash detected -> quarantine

    tif = _tif(tmp_path)  # zip is still there and gets extracted again
    assert quarantine.check_and_mark(tif) is False
    assert not tif.exists()  # re-extracted copy removed
    assert not quarantine.crashed_last_time(tif)


def test_other_files_are_not_affected(tmp_path: Path) -> None:
    bad, good = _tif(tmp_path, "bad.tif"), _tif(tmp_path, "good.tif")
    quarantine.check_and_mark(bad)  # crash while `bad` was in flight

    assert quarantine.check_and_mark(bad) is False
    assert quarantine.check_and_mark(good) is True
