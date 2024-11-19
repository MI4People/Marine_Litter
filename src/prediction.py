import concurrent.futures
import subprocess
import os
import time
import logging

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
            logging.info(f"Command '{command}' executed successfully.")
    
    except Exception as e:
        logging.error(f"An unexpected error occurred while executing command '{command}': {e}")

def show_progress(futures):
    """Track and log progress of parallel execution."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        
        # Log the progress in real-time
        logging.info(f"Progress: {done_count}/{total} completed, {running_count} running.", end='\r')
        
        if done_count == total:
            break
        
        time.sleep(1)

def main():
    # Define directories for input and output images
    input_folder = "src/resources/download_images"
    output_folder = "src/resources/predicted_images"
    
    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logging.info(f"Created output directory: {output_folder}")
    
    # Get a list of all .tif files in the input folder
    tif_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]
    if not tif_files:
        logging.warning("No TIFF files found in the input directory.")
        return

    # Define the command template for processing images
    commands = [
        f"marinedebrisdetector --device='cuda' --input {os.path.join(input_folder, tif_file)} --output {os.path.join(output_folder, tif_file)}"
        for tif_file in tif_files
    ]
    
    # Use ThreadPoolExecutor to run the commands in parallel (3 commands at a time)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_command, cmd) for cmd in commands]
        
        # Start a parallel task to show progress while the commands run
        show_progress(futures)
    
    logging.info("\nAll commands have been executed successfully.")
    
if __name__ == "__main__":
    main()
