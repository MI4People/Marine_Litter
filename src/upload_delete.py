import os
import logging
from google.cloud import storage

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DATES_PATH       = os.getenv("DATES_PATH")
GOOGLE_CRED_PATH = os.getenv("GOOGLE_CRED_PATH")
BUCKET_NAME      = os.getenv("BUCKET_NAME")
OUTPUT_PATH      = os.getenv("OUTPUT_PATH")

def upload_delete(bucket_name, source_folder, extra_file, credential):
    try:
        client = storage.Client.from_service_account_json(credential)
        bucket = client.bucket(bucket_name)

        # Prüfen, ob der Ordner existiert
        if not os.path.exists(source_folder):
            logging.error(f"Source folder '{source_folder}' does not exist.")
            return

        # Upload & Delete aller Dateien aus source_folder
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                source_file_path = os.path.join(root, file)
                destination_blob = os.path.relpath(source_file_path, source_folder).replace("\\", "/")

                try:
                    blob = bucket.blob(destination_blob)
                    blob.upload_from_filename(source_file_path)
                    logging.info(f"Uploaded: {source_file_path} -> {destination_blob}")  # per-file upload

                    os.remove(source_file_path)
                    logging.info(f"Deleted: {source_file_path}")  # per-file delete

                except Exception as e:
                    logging.error(f"Failed to upload {source_file_path}: {e}")  # upload error

        # Extra Datei hochladen (nicht löschen!)
        if os.path.exists(extra_file):
            destination_blob = os.path.basename(extra_file)
            try:
                blob = bucket.blob(destination_blob)
                blob.upload_from_filename(extra_file)
                logging.info(f"Uploaded extra file: {extra_file} -> {destination_blob}")  # extra-file upload
            except Exception as e:
                logging.error(f"Failed to upload extra file {extra_file}: {e}")  # extra-file error
        else:
            logging.warning(f"Extra file '{extra_file}' does not exist.")  # fehlende extra-file

        # Lokaler Snapshot nach Upload/Delete
        remaining_local = os.listdir(source_folder)
        logging.info(f"Directory snapshot after uploads & deletes: {remaining_local}")  # lokale Dateien

        # ——————————————
        # SERVER-SNAPSHOT: liste alle Objekte, die aktuell im Bucket liegen
        blobs = list(bucket.list_blobs())  
        blob_names = [b.name for b in blobs]
        logging.info(f"Server snapshot (bucket contents): {blob_names}")  # server-seitige Dateien

    except Exception as e:
        logging.critical(f"Error initializing storage client: {e}")

if __name__ == "__main__":
    upload_delete(
        bucket_name=BUCKET_NAME,
        source_folder=OUTPUT_PATH,
        extra_file=DATES_PATH,
        credential=GOOGLE_CRED_PATH
    )