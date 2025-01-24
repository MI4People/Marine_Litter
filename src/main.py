import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def execute_script(script_path, args=""):
    """Executes a given Python script with optional arguments."""
    try:
        command = f"python {script_path} {args}"
        logging.info(f"Executing: {command}")
        subprocess.run(command, shell=True, check=True)
        logging.info(f"Successfully executed: {script_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {script_path}: {e}")

def main():
    # Define script paths with correct relative paths
    scripts = {
        "order": "src/orderFromUp42.py",
        "predict": "src/prediction.py",
        "convert": "src/convert.py"
    }

    # Environment variables for order
    os.environ["DATE_FROM"] = "2023-01-01"
    os.environ["DATE_TO"] = "2023-01-20"
    os.environ["CONFIG_PATH"] = "src/resources/config.json"

    # Execute scripts in sequence
    logging.info("Starting workflow...")
    execute_script(scripts["order"])
    execute_script(scripts["predict"])
    execute_script(scripts["convert"])
    logging.info("Workflow completed successfully.")

if __name__ == "__main__":
    main()
