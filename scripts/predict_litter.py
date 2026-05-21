import concurrent.futures
import json
import logging
import os
import re
import shutil
import time
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from concurrent.futures import Future
from pathlib import Path

import torch
from torch.cuda.random import device_count

from marine_litter.ml_settings import MLSettings
from marine_litter.tif_processing import predict_litter
from marine_litter.zip_processing import process_zip

log = logging.getLogger(__name__)


def show_progress(futures: list[Future[Path | None]]) -> None:
    """Track and log progress of parallel execution."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        print(f"  {done_count}/{total} completed, {running_count} running.", end="\r")
        if done_count == total:
            break
        time.sleep(5)


def move_predictions_to_output_path(input_path: Path, output_path: Path) -> list[Path]:
    """Move predicted files to output directory.
    :param input_path: directory containing the original TIFFs and the predicted TIFFs
    :param output_path: directory to move the predicted TIFFs to
    :returns: list of moved files
    """
    moved_files = []
    for prediction_tif in input_path.glob("*_prediction.tif"):
        try:
            shutil.move(prediction_tif, output_path / prediction_tif.name)
            moved_files.append(prediction_tif)
            log.info(f"Moved '{prediction_tif.name}' to {output_path}/")
        except Exception as e:
            log.error(f"Failed to move '{prediction_tif.name}': {e}")

    return moved_files


def cleanup_input_directory(input_path: Path) -> None:
    """Remove the litter prediction input TIFFs.
    :param input_path: directory containing the TIFFs to be deleted
    """
    for tif_file in input_path.glob("*.tif"):
        tif_file.unlink()
        log.debug(f"Deleted '{tif_file.name}'")


def update_dates_json(dates_path: Path, predicted_files: list[Path]) -> None:
    json_data: dict[str, list[str]] = {}
    if dates_path.exists():
        with dates_path.open("r", encoding="utf-8") as json_file:
            try:
                json_data = json.load(json_file)
            except json.JSONDecodeError:
                log.warning(f"Could not load '{dates_path}'. Re-creating file.")

    new_dates = defaultdict(list)
    for json_key, json_values in json_data.items():
        new_dates[json_key].extend(json_values)
    for predicted in sorted(predicted_files):
        filename = predicted.name
        m = re.search(r"_(20\d{2})(\d{2})(\d{2})T\d{6}_", filename)
        if not m:
            log.warning(f"Could not extract date from '{filename}'")
            continue
        new_dates[f"{m.group(1)}-{m.group(2)}-{m.group(3)}"].append(filename)

    with dates_path.open("w", encoding="utf-8") as json_file:
        json.dump(new_dates, json_file, indent=4)
    log.info(f"Updated {dates_path} with {len(predicted_files)} predicted file(s)")


def _extract_tiff_files(input_path: Path) -> None:
    """Extract all .tif files from .zip archives in the input directory."""
    zip_files = sorted(input_path.glob("*.zip"))
    if not zip_files:
        log.warning(f"No UP42 zip files found in '{input_path}'!")
        return

    for i, zip_file in enumerate(zip_files):
        log.info(f"Processing {i + 1:2}/{len(zip_files)} '{zip_file.name}'")
        process_zip(zip_file)
        log.info(f"-> Extracted TIFFs from '{zip_file.name}'")


def main(
    settings: MLSettings | None = None,
    delete_zip: bool = True,
    dry_run: bool = False,
    delete_input: bool = True,
) -> None:
    if settings is None:
        settings = MLSettings(".env")
        logging.basicConfig(level=settings.log_level, format=settings.log_format)
        log.info(f"Settings:\n{settings.as_table()}")

    log.info(10 * "-" + " Run prediction on images")

    if dry_run:
        return

    input_path = settings.input_path
    _extract_tiff_files(input_path)

    tif_files = sorted(input_path.glob("*.tif"))
    if not tif_files:
        log.warning(f"No tif files found in '{input_path}'!")
        return

    output_path = settings.output_path
    if output_path.exists():
        shutil.rmtree(output_path)
        log.info(f"Cleared existing output directory: '{output_path}'")
    output_path.mkdir(parents=True, exist_ok=True)
    log.info(f"Created output directory: {output_path}")

    device = settings.device
    if device == "cuda" and (device_count() == 0 or not torch.cuda.is_available()):
        log.warning("No CUDA devices found, falling back to CPU")
        device = "cpu"

    checkpoint_path = None
    if settings.checkpoint_file:
        checkpoint_path = settings.checkpoints.expanduser() / settings.checkpoint_file
        if not checkpoint_path.exists():
            log.warning(f"Custom checkpoint not found: {checkpoint_path}, using hub defaults")
            checkpoint_path = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.predict_workers) as executor:
        futures = [executor.submit(predict_litter, tif_file, device, checkpoint_path) for tif_file in tif_files]
        show_progress(futures)

    predicted_files = [f.result() for f in futures if f.result() is not None]
    log.info(f"Successfully predicted {len(predicted_files)}/{len(tif_files)} files")

    moved_files: list[Path] = move_predictions_to_output_path(input_path, output_path)

    if delete_input:
        cleanup_input_directory(input_path)

    if delete_zip:
        for zip_file in input_path.glob("*.zip"):
            try:
                zip_file.unlink()
                log.info(f"Deleted '{zip_file.name}'")
            except Exception as e:
                log.error(f"Failed to delete '{zip_file.name}': {e}")

    update_dates_json(settings.dates_path, moved_files)


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])

    ap = ArgumentParser(description="Run marine litter prediction on TIFF files extracted from UP42 zip archives.")
    ap.add_argument("-d", "--dry-run", action="store_true", help="only tell settings and do some checks")
    ap.add_argument("--delete-zip", action="store_true", help="delete zip files after processing")
    ap.add_argument(
        "--no-delete-zip", action="store_false", dest="delete_zip", help="do not delete zip files after processing"
    )
    ap.add_argument("--delete-input", action="store_true", help="delete input TIFF files after processing")
    ap.add_argument(
        "--no-delete-input",
        action="store_false",
        dest="delete_input",
        help="do not delete input TIFF files after processing",
    )
    args: Namespace = ap.parse_args()

    main(dry_run=args.dry_run, delete_zip=args.delete_zip, delete_input=args.delete_input)
