import concurrent.futures
import json
import logging
import os
import re
import shutil
import time
from collections import defaultdict
from pathlib import Path

from marine_litter.ml_settings import MLSettings
from marine_litter.tif_processing import predict_litter
from marine_litter.zip_processing import process_zip

log = logging.getLogger(__name__)


def show_progress(futures):
    """Track and log progress of parallel execution."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        print(f"  {done_count}/{total} completed, {running_count} running.", end="\r")
        if done_count == total:
            break
        time.sleep(5)


def move_predictions_and_remove_prediction_input_files(input_path: Path, output_path: Path) -> list[Path]:
    moved_files = []
    for prediction_tif in input_path.glob("*_prediction.tif"):
        try:
            shutil.move(prediction_tif, output_path / prediction_tif.name)
            moved_files.append(prediction_tif)
            log.info(f"Moved '{prediction_tif.name}' to {output_path}/")
        except Exception as e:
            log.error(f"Failed to move '{prediction_tif.name}': {e}")

    # remove the litter prediction input TIFFs
    for tif_file in input_path.glob("*.tif"):
        tif_file.unlink()
        log.debug(f"Deleted '{tif_file.name}'")

    return moved_files


def update_dates_json(dates_path: Path, predicted_files: list[Path]):
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


def main(settings: MLSettings | None = None, delete_zip: bool = True, dry_run: bool = False):
    if settings is None:
        settings = MLSettings(".env")
        logging.basicConfig(level=settings.log_level, format=settings.log_format)
        log.info(f"Settings:\n{settings.as_table()}")

    log.info(10 * "-" + " Run prediction on images")
    input_path = settings.input_path
    zip_files = sorted(input_path.glob("*.zip"))

    if dry_run:
        return

    if not zip_files:
        log.warning(f"No UP42 zip files found in '{input_path}'!")
        return

    for i, zip_file in enumerate(zip_files):
        log.info(f"Processing {i + 1:2}/{len(zip_files)} '{zip_file.name}'")
        tif_fname: Path = process_zip(zip_file)
        if delete_zip:
            zip_file.unlink()
        log.info(f"-> '{tif_fname}'")

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

    checkpoint_path = None
    if settings.checkpoint_file:
        checkpoint_path = settings.checkpoints.expanduser() / settings.checkpoint_file
        if not checkpoint_path.exists():
            log.warning(f"Custom checkpoint not found: {checkpoint_path}, using hub defaults")
            checkpoint_path = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.predict_workers) as executor:
        futures = [
            executor.submit(predict_litter, tif_file, settings.device, checkpoint_path) for tif_file in tif_files
        ]
        show_progress(futures)

    predicted_files = [f.result() for f in futures if f.result() is not None]
    log.info(f"Successfully predicted {len(predicted_files)}/{len(tif_files)} files")

    moved_files: list[Path] = move_predictions_and_remove_prediction_input_files(input_path, output_path)
    update_dates_json(settings.dates_path, moved_files)


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])
    main()
