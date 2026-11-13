"""Quarantine for input files that crash the prediction process.

A crash in native code (segfault in GDAL, Torch, CUDA) kills the process without a Python exception, so the
failing file cannot be caught with try/except. Without protection the file stays in the input folder, is picked
up again on the next run and crashes it again, night after night.

Protection works with a marker file per input:
- before the prediction starts, an `.inprogress` marker is written next to the input file,
- after the prediction finished (successfully or with a Python exception) the marker is removed,
- if a marker is found at the start, the previous run died while processing this file: the file is moved to the
  quarantine folder and skipped from now on.

With parallel prediction workers all files in flight at the time of the crash get a marker, so innocent files
may land in quarantine as well. They are kept (not deleted) and can be processed again manually.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

QUARANTINE_DIR_NAME = "_quarantine"


def quarantine_dir(input_file: Path) -> Path:
    return input_file.parent / QUARANTINE_DIR_NAME


def _marker(input_file: Path) -> Path:
    return input_file.parent / f".{input_file.name}.inprogress"


def _record(input_file: Path) -> Path:
    return quarantine_dir(input_file) / f"{input_file.name}.txt"


def is_quarantined(input_file: Path) -> bool:
    """True if the file was put into quarantine in an earlier run."""
    return _record(input_file).exists()


def crashed_last_time(input_file: Path) -> bool:
    """True if a marker from an earlier, crashed run exists for this file."""
    return _marker(input_file).exists()


def mark_in_progress(input_file: Path) -> None:
    _marker(input_file).write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")


def clear_in_progress(input_file: Path) -> None:
    _marker(input_file).unlink(missing_ok=True)


def put_into_quarantine(input_file: Path, reason: str) -> None:
    """Move the input file into the quarantine folder and write a record, so it is skipped from now on."""
    qdir = quarantine_dir(input_file)
    qdir.mkdir(parents=True, exist_ok=True)
    started = _marker(input_file).read_text(encoding="utf-8") if _marker(input_file).exists() else "unknown"
    _record(input_file).write_text(
        f"file:          {input_file.name}\n"
        f"quarantined:   {datetime.now(timezone.utc).isoformat()}\n"
        f"crashed run:   {started}\n"
        f"reason:        {reason}\n",
        encoding="utf-8",
    )
    if input_file.exists():
        shutil.move(str(input_file), str(qdir / input_file.name))
    clear_in_progress(input_file)
    log.error(f"QUARANTINE '{input_file.name}': {reason} -> moved to '{qdir}'")


def check_and_mark(input_file: Path) -> bool:
    """Gate before a prediction. Returns True if the file may be processed, False if it has to be skipped.

    Skips files that were quarantined earlier (and removes their re-extracted copy) and quarantines files whose
    marker shows that the previous run crashed while processing them. Otherwise sets the marker.
    """
    if is_quarantined(input_file):
        input_file.unlink(missing_ok=True)
        log.warning(f"QUARANTINE '{input_file.name}': skipped, quarantined in an earlier run")
        return False
    if crashed_last_time(input_file):
        put_into_quarantine(input_file, "previous run crashed while predicting this file")
        return False
    mark_in_progress(input_file)
    return True
