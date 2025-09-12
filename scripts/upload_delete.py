import logging
from pathlib import Path

from google.cloud import storage

from marine_litter.ml_settings import MLSettings


def upload_delete(bucket_name, source_folder, extra_file, credential):
    try:
        client = storage.Client.from_service_account_json(str(credential))
        bucket = client.bucket(bucket_name)

        source_folder = Path(source_folder)
        extra_file = Path(extra_file)

        if not source_folder.exists():
            logging.error(f"Source folder '{source_folder}' does not exist.")
            return

        for source_file_path in source_folder.rglob("*"):
            if source_file_path.is_file():
                destination_blob = str(source_file_path.relative_to(source_folder)).replace("\\", "/")
                try:
                    blob = bucket.blob(destination_blob)
                    blob.upload_from_filename(str(source_file_path))
                    logging.info(f"Uploaded: {source_file_path} -> {destination_blob}")

                    source_file_path.unlink()
                    logging.info(f"Deleted: {source_file_path}")

                except Exception as e:
                    logging.error(f"Failed to upload {source_file_path}: {e}")

        if extra_file.exists():
            destination_blob = extra_file.name
            try:
                blob = bucket.blob(destination_blob)
                blob.upload_from_filename(str(extra_file))
                logging.info(f"Uploaded extra file: {extra_file} -> {destination_blob}")
            except Exception as e:
                logging.error(f"Failed to upload extra file {extra_file}: {e}")
        else:
            logging.warning(f"Extra file '{extra_file}' does not exist.")

        logging.info(f"Directory snapshot after uploads & deletes: {[f.name for f in source_folder.iterdir()]}")

        blobs = list(bucket.list_blobs())
        blob_names = [b.name for b in blobs]
        logging.info(f"Server snapshot (bucket contents): {blob_names}")

    except Exception as e:
        logging.critical(f"Error initializing storage client: {e}")


def run_upload_delete(settings: MLSettings = None):
    if settings is None:
        settings = MLSettings()
    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    logging.info(10 * "-" + " Upload and delete images")

    upload_delete(
        bucket_name=settings.bucket_name,
        source_folder=settings.output_path,
        extra_file=settings.dates_path,
        credential=settings.google_cred_path,
    )


if __name__ == "__main__":
    run_upload_delete()
