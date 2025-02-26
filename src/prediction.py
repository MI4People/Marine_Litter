import concurrent.futures
import subprocess
import os
import time
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command):
    """Run the command to process each image and log progress."""
    try:
        # Log the command being executed
        logging.info(f"Executing command: {command}")
        
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Print the output of the process in real-time
        for line in process.stdout:
            logging.info(line.strip())
        
        process.wait()
        
        if process.returncode != 0:
            # Log errors if the command fails
            error_msg = process.stderr.read()
            logging.error(f"Error while executing command '{command}': {error_msg}")
        else:
            logging.info(f"Command executed successfully.")
    
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
    """Move predicted files from input folder to output folder."""
    for file_name in os.listdir(input_folder):
        if file_name.endswith("_prediction.tif"):
            src_path = os.path.join(input_folder, file_name)
            dst_path = os.path.join(output_folder, file_name)
            try:
                shutil.move(src_path, dst_path)
                logging.info(f"Moved prediction {file_name} to {output_folder}")
            except Exception as e:
                logging.error(f"Failed to move {file_name}: {e}")

def main():
    # Define directories for input and output images
    input_folder = "images/downloaded"
    # Predictions are initially saved in the input folder; we'll move them later.
    output_folder = "images/predicted"
    
    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.info(f"Created output directory: {output_folder}")
    
    # Get a list of all .tif files in the input folder
    tif_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]
    if not tif_files:
        logging.warning("No TIFF files found in the input directory.")
        return

    # Define the command template (only the positional input argument is needed)
    commands = [
        f"marinedebrisdetector --device=cuda {os.path.join(input_folder, tif_file)}"
        for tif_file in tif_files
    ]
    
    # Use ThreadPoolExecutor with max_workers=1 to run the commands serially
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        
        # Show progress while the commands run
        show_progress(futures)
    
    logging.info("All prediction commands have been executed.")
    
    # Move predicted images from the input folder to the output folder
    move_predictions(input_folder, output_folder)
    
    logging.info("Workflow completed successfully.")

if __name__ == "__main__":
    main()
