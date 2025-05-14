import concurrent.futures
import subprocess
import os
import time
import logging
import shutil
import json
import datetime

# Configure logging
testing_format='%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=testing_format)

DAYBEFORE = int(os.environ.get("DAYBEFORE", 2))
WORKERS = int(os.environ.get("WORKERS", 1))
DEVICE = os.environ.get("DEVICE", "cuda")
DATES_PATH = os.getenv("DATES_PATH")
INPUT_PATH = os.getenv("INPUT_PATH")
OUTPUT_PATH = os.getenv("OUTPUT_PATH")


def run_command(command):
    """Run the command to process each image and log progress."""
    try:
        logging.info(f"Executing command: {command}")
        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
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
    """Move predicted files from input folder to output folder and return moved filenames."""
    moved_files = []
    for file_name in os.listdir(input_folder):
        if file_name.endswith("_prediction.tif"):
            src_path = os.path.join(input_folder, file_name)
            dst_path = os.path.join(output_folder, file_name)
            try:
                shutil.move(src_path, dst_path)
                moved_files.append(file_name)
                logging.info(f"Moved prediction {file_name} to {output_folder}")
            except Exception as e:
                logging.error(f"Failed to move {file_name}: {e}")
    return moved_files


def update_dates_json(json_path, predicted_files):
    """Update JSON file with yesterday's date and provided predicted filenames without duplicates."""
    yesterday = (datetime.date.today() - datetime.timedelta(days=DAYBEFORE)).isoformat()

    # Load or initialize JSON data
    if os.path.exists(json_path):
        with open(json_path, "r") as json_file:
            try:
                json_data = json.load(json_file)
            except json.JSONDecodeError:
                logging.warning(f"Corrupted JSON found at {json_path}. Re-creating file.")
                json_data = {}
    else:
        json_data = {}

    # Ensure bucket for yesterday exists
    json_data.setdefault(yesterday, [])

    # Append only new files for that date
    for file in predicted_files:
        if file not in json_data[yesterday]:
            json_data[yesterday].append(file)

    # Deduplicate and sort
    json_data[yesterday] = sorted(set(json_data[yesterday]))

    # Write out
    with open(json_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    logging.info(f"Updated JSON for {yesterday} with files: {predicted_files}")


def clean_input_folder(input_folder):
    """Delete all files in the input folder after processing."""
    try:
        for file_name in os.listdir(input_folder):
            file_path = os.path.join(input_folder, file_name)
            os.remove(file_path)
            logging.info(f"Deleted: {file_name}")
        logging.info("All input files deleted successfully.")
    except Exception as e:
        logging.error(f"Error while deleting files from input folder: {e}")


def main():
    # Ensure output folder is fresh
    if os.path.exists(OUTPUT_PATH):
        shutil.rmtree(OUTPUT_PATH)
        logging.info(f"Cleared existing output directory: {OUTPUT_PATH}")
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    logging.info(f"Created output directory: {OUTPUT_PATH}")

    tif_files = [f for f in os.listdir(INPUT_PATH) if f.endswith(".tif")]
    if not tif_files:
        logging.warning("No TIFF files found in the input directory.")
        return

    commands = [
        f"marinedebrisdetector --device={DEVICE} {os.path.join(INPUT_PATH, tif_file)}"
        for tif_file in tif_files
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        show_progress(futures)
    logging.info("All prediction commands have been executed.")

    # Move predicted images and capture filenames
    moved_files = move_predictions(INPUT_PATH, OUTPUT_PATH)

    # Update JSON with only today's predictions
    update_dates_json(DATES_PATH, moved_files)

    # Clean up input folder
    clean_input_folder(INPUT_PATH)

    logging.info("Workflow completed successfully.")


if __name__ == "__main__":
    main()