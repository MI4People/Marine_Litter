import argparse
import logging
import os
from pathlib import Path

from google.cloud import storage

from marine_litter.ml_settings import MLSettings

log = logging.getLogger(__name__)


def upload_delete(
    bucket_name: str,
    source_folder: Path,
    prediction_tifs_by_date_json: Path,
    google_creds_path: Path,
) -> None:
    """Upload predicted tif files to Google Cloud Storage and delete them locally.
    :param bucket_name: name of the Google Cloud Storage bucket to upload to
    :param source_folder: local directory containing the predicted tif files to upload
    :param prediction_tifs_by_date_json: local path to the JSON file containing prediction tif filenames by date
    :param google_creds_path: local path to the Google Cloud service account credentials JSON file
    """
    if not source_folder.is_dir():
        log.error(f"Source folder '{source_folder}' does not exist.")
        return

    bucket = None
    try:
        client = storage.Client.from_service_account_json(google_creds_path)
        bucket = client.bucket(bucket_name)
    except Exception as e:
        log.critical(f"Error for GC storage client: {e}")
    if bucket is None:
        return

    # 1) upload prediction tifs and delete them locally
    for source_file in source_folder.glob("*.tif"):
        source_file: Path
        destination_blob = source_file.name
        try:
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(str(source_file))
            log.info(f"✓ {destination_blob}")

            source_file.unlink()
            log.debug(f"Deleted: {source_file}")

        except Exception as e:
            log.error(f"Failed to upload {source_file}: {e}")

    # 2) upload 'dates.json': prediction tif filenames by date
    if prediction_tifs_by_date_json.exists():
        destination_blob = prediction_tifs_by_date_json.name
        try:
            blob = bucket.blob(destination_blob)
            blob.upload_from_filename(str(prediction_tifs_by_date_json))
            log.info(f"Uploaded extra file: {prediction_tifs_by_date_json} -> {destination_blob}")
        except Exception as e:
            log.error(f"Failed to upload extra file {prediction_tifs_by_date_json}: {e}")
    else:
        log.warning(f"Extra file '{prediction_tifs_by_date_json}' does not exist.")

    if not "unclear why this is needed, and how to sort":
        max_results = 100
        log.info(f"Server bucket contents (max. {max_results}):")
        blob_names = sorted(b.name for b in bucket.list_blobs(max_results=max_results))
        log.info("\n  ".join(["\n"] + [str(r) for r in blob_names]))


def main(settings: MLSettings | None = None, dry_run: bool = False) -> None:
    if settings is None:
        settings = MLSettings(".env")
        logging.basicConfig(level=settings.log_level, format=settings.log_format)
        log.info(f"Settings:\n{settings.as_table()}")

    log.info(10 * "-" + " Upload and delete images")
    if dry_run:
        return

    upload_delete(
        bucket_name=settings.bucket_name,
        source_folder=settings.output_path,
        prediction_tifs_by_date_json=settings.dates_path,
        google_creds_path=settings.google_creds_path,
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])
    ap = argparse.ArgumentParser(
        description="Upload predicted tif files to Google Cloud Storage and delete them locally."
    )
    ap.add_argument("--dry-run", action="store_true", help="Run the script without performing uploads or deletions.")
    args = ap.parse_args()
    main(dry_run=args.dry_run)
