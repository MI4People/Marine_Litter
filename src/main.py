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
        "convert": "src/convert.py",
        "upload_delete": "src/upload_delete.py"
    }

    # Environment variables for order
    os.environ["CONFIG_PATH"] = "src/resources/config.geojson"
    os.environ["DATES_PATH"] = "src/resources/dates.json"
    os.environ["INPUT_PATH"] = "images/downloaded"
    os.environ["OUTPUT_PATH"] = "images/predicted"
    os.environ["UP42_CRED_PATH"] = "secrets/up42_credentials.json"
    os.environ["GOOGLE_CRED_PATH"] = "secrets/google_credentials.json"
    os.environ["BUCKET_NAME"] = "marinelitter_predicted"
    os.environ["WORKERS"] = "10"

    # Execute scripts in sequence
    logging.info("--------------Starting workflow--------------")
    logging.info("--------------Order and Download Images--------------")
    execute_script(scripts["order"])
    logging.info("--------------Analise Images--------------")
    execute_script(scripts["predict"])
    logging.info("--------------Convert Images--------------")
    execute_script(scripts["convert"])
    logging.info("--------------Upload and Delete Images--------------")
    execute_script(scripts["upload_delete"])
    logging.info("--------------Workflow completed successfully.--------------")

if __name__ == "__main__":
    main()
