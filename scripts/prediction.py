import concurrent.futures
import datetime
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

from marine_litter.ml_settings import MLSettings


def run_command(command):
    """Run the command to process each image and log progress."""
    try:
        logging.info(f"Executing command: {command}")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in process.stdout:
            logging.info(line.strip())
        process.wait()
        if process.returncode != 0:
            error_msg = process.stderr.read()
            logging.error(f"Error while executing command '{command}': {error_msg}")
        else:
            logging.info("Command executed successfully.")
    except Exception as e:
        logging.error(f"An unexpected error occurred while executing command '{command}': {e}")


def show_progress(futures):
    """Track and log progress of parallel execution."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        logging.info(f"Progress: {done_count}/{total} completed, {running_count} running.")
        if done_count == total:
            break
        time.sleep(5)


def move_predictions(input_folder, output_folder):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    moved_files = []
    for file_path in input_folder.iterdir():
        if file_path.name.endswith("_prediction.tif"):
            dst_path = output_folder / file_path.name
            try:
                shutil.move(str(file_path), str(dst_path))
                moved_files.append(file_path.name)
                logging.info(f"Moved prediction {file_path.name} to {output_folder}")
            except Exception as e:
                logging.error(f"Failed to move {file_path.name}: {e}")
    return moved_files


def update_dates_json(json_path, predicted_files, days_before):
    json_path = Path(json_path)
    yesterday = (datetime.date.today() - datetime.timedelta(days=days_before)).isoformat()
    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as json_file:
            try:
                json_data = json.load(json_file)
            except json.JSONDecodeError:
                logging.warning(f"Corrupted JSON found at {json_path}. Re-creating file.")
                json_data = {}
    else:
        json_data = {}
    json_data.setdefault(yesterday, [])
    for file in predicted_files:
        if file not in json_data[yesterday]:
            json_data[yesterday].append(file)
    json_data[yesterday] = sorted(set(json_data[yesterday]))
    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, indent=4)
    logging.info(f"Updated JSON for {yesterday} with files: {predicted_files}")


def clean_input_folder(input_folder):
    input_folder = Path(input_folder)
    try:
        for file_path in input_folder.iterdir():
            file_path.unlink()
            logging.info(f"Deleted: {file_path.name}")
        logging.info("All input files deleted successfully.")
    except Exception as e:
        logging.error(f"Error while deleting files from input folder: {e}")


def run_prediction(settings: MLSettings = None):
    if settings is None:
        settings = MLSettings()
    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    logging.info(10 * "-" + " Run prediction on images")

    output_path = Path(settings.output_path)
    input_path = Path(settings.input_path)
    if output_path.exists():
        shutil.rmtree(output_path)
        logging.info(f"Cleared existing output directory: {output_path}")
    output_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Created output directory: {output_path}")
    tif_files = [f for f in input_path.iterdir() if f.name.endswith(".tif")]
    if not tif_files:
        logging.warning("No TIFF files found in the input directory.")
        return
    commands = [f"marinedebrisdetector --device={settings.device} {str(tif_file)}" for tif_file in tif_files]
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.predict_workers) as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        show_progress(futures)
    moved_files = move_predictions(input_path, output_path)
    update_dates_json(settings.dates_path, moved_files, settings.days_before)
    clean_input_folder(input_path)


if __name__ == "__main__":
    run_prediction()
