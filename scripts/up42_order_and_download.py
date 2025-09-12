import concurrent.futures
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from urllib3.exceptions import ReadTimeoutError

try:
    import up42  # strangely goes online for version check. Trying again in case of a timeout may help.
except ReadTimeoutError:
    import up42
from up42 import Catalog

from marine_litter.ml_settings import MLSettings


def process_order(image_id: str, geometry: dict, input_path: str, catalog: Catalog, product_id: str) -> dict:
    """Call catalog.place_order(), wait for fulfillment, then download each via asset.file.download()."""
    try:
        logging.info(f"Processing order for image {image_id}")

        # 1) Build and place order
        order_params = catalog.construct_order_parameters(
            data_product_id=product_id,
            image_id=image_id,
            aoi=geometry,
        )
        order = catalog.place_order(order_params)
        order_id = order.order_id  # old‐style attribute
        logging.info(f"Order {order_id} placed for image {image_id}")

        # 2) Poll until FULFILLED or FAILED
        while order.status not in {"FULFILLED", "FAILED"}:
            time.sleep(60)
            order.track_status(report_time=60)
            logging.info(f"Order {order_id} status: {order.status}")

        if order.status == "FAILED":
            logging.error(f"Order {order_id} failed")
            return {"order_id": order_id, "image_id": image_id, "status": "FAILED", "assets_processed": 0}

        # 3) Download assets (if any)
        assets = order.get_assets()
        logging.info(f"Order {order_id} fulfilled with {len(assets)} assets")
        if not assets:
            return {"order_id": order_id, "image_id": image_id, "status": "FULFILLED", "assets_processed": 0}

        Path(input_path).mkdir(parents=True, exist_ok=True)
        assets_processed = 0
        logging.getLogger("tqdm").setLevel(logging.ERROR)  # silence tqdm   TODO fix
        asset = None
        try:
            for asset in assets:
                asset.file.download(input_path)  # TODO deprecated
                logging.info(f"'{image_id}' downloaded for order {order_id}")
                assets_processed += 1
        except Exception as e:
            logging.exception(f"Error downloading '{image_id}' for order {order_id}: {e}")

        logging.info(f"Directory snapshot after downloads: {os.listdir(input_path)}")

        return {"order_id": order_id, "image_id": image_id, "status": "FULFILLED", "assets_processed": assets_processed}

    except Exception as e:
        logging.exception(f"Error in process_order() for {image_id} ({e})")
        return {"image_id": image_id, "status": "ERROR", "error": "see logs", "assets_processed": 0}


def run_order_and_download_from_up42(settings: MLSettings = None):
    """Workflow step: authenticate, search, order, and download images from UP42."""
    if settings is None:
        settings = MLSettings()
    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    logging.info(10 * "-" + " Run order and download images")

    try:
        up42_cred_path = Path(settings.up42_cred_path)
        config_path = Path(settings.config_path)
        input_path = Path(settings.input_path)
        if not up42_cred_path.exists():
            raise FileNotFoundError(f"Credentials file not found at {up42_cred_path}")

        with up42_cred_path.open(encoding="utf-8") as f:
            creds = json.load(f)

        up42.authenticate(username=creds["username"], password=creds["password"])
        logging.info("Successfully authenticated with UP42")

        with config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        geom = config["features"][0]["geometry"]
        geometry = {"type": geom["type"], "coordinates": geom["coordinates"]}
        product_id = config.get("product_id", settings.product_id)

        date_of_interest = (date.today() - timedelta(days=settings.days_before)).strftime("%Y-%m-%d")
        logging.info(f"Date of interest is: {date_of_interest}")

        catalog = up42.initialize_catalog()
        search_params = catalog.construct_search_parameters(
            collections=["sentinel-2"],
            geometry=geometry,
            start_date=date_of_interest,
            end_date=date_of_interest,
            max_cloudcover=100,
            limit=10,
        )
        search_results_df = catalog.search(search_params)  # TODO deprecated
        logging.info(f"Found {len(search_results_df)} images matching criteria")
        if search_results_df.empty:
            logging.info("No images found; exiting.")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.order_workers) as executor:
            futures = [
                executor.submit(
                    process_order,
                    getattr(row, "id", row[1]),
                    geometry,
                    str(input_path),
                    catalog,
                    product_id,
                )
                for row in search_results_df.itertuples()
            ]

            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                res = future.result()
                logging.info(f"Progress: {idx}/{len(futures)} → {res}")

        logging.info("All orders have been processed")

    except Exception as e:
        logging.error(f"Error in download_from_up42: {e}")
        raise


if __name__ == "__main__":
    run_order_and_download_from_up42()
