import os
import logging
from google.cloud import storage

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def upload_delete(bucket_name, source_folder, extra_file, credential):
    try:
        client = storage.Client.from_service_account_json(credential)
        bucket = client.bucket(bucket_name)

        # Prüfen, ob der Ordner existiert
        if not os.path.exists(source_folder):
            logging.error(f"Source folder '{source_folder}' does not exist.")
            return

        # Hochladen aller Dateien aus images/predicted
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                source_file_path = os.path.join(root, file)
                destination_blob = os.path.relpath(source_file_path, source_folder).replace("\\", "/")

                try:
                    blob = bucket.blob(destination_blob)
                    blob.upload_from_filename(source_file_path)
                    logging.info(f"Uploaded: {source_file_path} -> {destination_blob}")

                    # Löschen der Datei nur, wenn Upload erfolgreich war
                    os.remove(source_file_path)
                    logging.info(f"Deleted: {source_file_path}")

                except Exception as e:
                    logging.error(f"Failed to upload {source_file_path}: {e}")

        # Extra Datei hochladen (nicht löschen!)
        if os.path.exists(extra_file):
            destination_blob = os.path.basename(extra_file)  # Speichert sie mit ihrem Dateinamen im Root des Buckets
            try:
                blob = bucket.blob(destination_blob)
                blob.upload_from_filename(extra_file)
                logging.info(f"Uploaded extra file: {extra_file} -> {destination_blob}")
            except Exception as e:
                logging.error(f"Failed to upload extra file {extra_file}: {e}")
        else:
            logging.warning(f"Extra file '{extra_file}' does not exist.")

    except Exception as e:
        logging.critical(f"Error initializing storage client: {e}")

if __name__ == "__main__":
    upload_delete(
        bucket_name="marinelitter_predicted",
        source_folder="images/predicted",
        extra_file="src/resources/dates.json",
        credential="src/credentials.json"
    )
