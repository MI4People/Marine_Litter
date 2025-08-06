import os
import json
import logging
import concurrent.futures
import time
import up42
from datetime import date, timedelta

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.zip_processing import process_zip

# ——————————————————————————————————————————————————————————————
# Configure root logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# Enable debug logging in the UP42 SDK itself
logging.getLogger("up42").setLevel(logging.DEBUG)  # show SDK internals

DAYBEFORE      = int(os.environ.get("DAYBEFORE", 2))
CONFIG_PATH    = os.getenv("CONFIG_PATH")
INPUT_PATH     = os.getenv("INPUT_PATH")
UP42_CRED_PATH = os.getenv("UP42_CRED_PATH")
ORDER_WORKERS  = int(os.environ.get("ORDER_WORKERS", 3))


def process_order(image_id: str, geometry: dict, input_path: str, catalog) -> dict:
    """
    Place an order → poll until ready → download each asset.
    """
    try:
        logging.info(f"Processing order for image {image_id}")  # start order

        # 1) Build and place order
        order_params = catalog.construct_order_parameters(
            data_product_id=PRODUCT_ID,
            image_id=image_id,
            aoi=geometry,
        )
        order = catalog.place_order(order_params)
        order_id = order.order_id
        logging.info(f"Order {order_id} placed for image {image_id}")  # order sent

        # 2) Poll until FULFILLED or FAILED
        while order.status not in ("FULFILLED", "FAILED"):
            time.sleep(60)
            order.track_status(report_time=60)
            logging.info(f"Order {order_id} status: {order.status}")  # status update

        if order.status == "FAILED":
            logging.error(f"Order {order_id} failed")  # order failed
            return {
                "order_id": order_id,
                "image_id": image_id,
                "status": "FAILED",
                "assets_processed": 0
            }

        # 3) Download assets
        assets = order.get_assets()
        logging.info(f"Order {order_id} fulfilled with {len(assets)} assets")  # count assets
        if not assets:
            return {
                "order_id": order_id,
                "image_id": image_id,
                "status": "FULFILLED",
                "assets_processed": 0
            }

        os.makedirs(input_path, exist_ok=True)
        assets_processed = 0

        # Silence tqdm noise if it’s used internally
        logging.getLogger("tqdm").setLevel(logging.ERROR)

        for asset in assets:
            try:
                # build full download target path
                fname = asset.file.name or f"{asset.asset_id}.dat"
                target = os.path.join(input_path, fname)
                logging.debug(f"Downloading asset to: {target}")  # show intended filepath

                asset.file.download(input_path)  # actual download

                # verify file presence
                if os.path.exists(target):
                    logging.info(f"✔ Confirmed download of {target}")  # success check
                else:
                    logging.error(f"✖ Download claimed success but file missing at {target}")  # missing file

                assets_processed += 1

            except Exception:
                logging.exception(f"Error downloading asset {asset.asset_id or asset.file.id} for order {order_id}")  # full stack

        # snapshot directory after downloads
        downloaded_files = os.listdir(input_path)
        logging.info(f"Directory snapshot after downloads: {downloaded_files}")  # what landed

        return {
            "order_id": order_id,
            "image_id": image_id,
            "status": "FULFILLED",
            "assets_processed": assets_processed
        }

    except Exception:
        logging.exception(f"Error in process_order for {image_id}")  # full stack on top-level failure
        return {
            "image_id": image_id,
            "status": "ERROR",
            "error": "see logs",
            "assets_processed": 0
        }


def download_from_up42(config_path):
    """
    Authenticate → search → place orders in parallel → download assets.
    """
    try:
        if not os.path.exists(UP42_CRED_PATH):
            raise FileNotFoundError(f"Credentials file not found at {UP42_CRED_PATH}")

        with open(UP42_CRED_PATH) as f:
            creds = json.load(f)

        up42.authenticate(username=creds["username"], password=creds["password"])
        logging.info("Successfully authenticated with UP42")  # auth OK

        with open(config_path) as f:
            config = json.load(f)

        geom = config["features"][0]["geometry"]
        geometry = {"type": geom["type"], "coordinates": geom["coordinates"]}
        global PRODUCT_ID
        PRODUCT_ID = config.get("product_id", "c3de9ed8-f6e5-4bb5-a157-f6430ba756da")

        date_of_interest = (date.today() - timedelta(days=DAYBEFORE)).strftime("%Y-%m-%d")
        logging.info(f"Date of interest is: {date_of_interest}")  # which date

        catalog = up42.initialize_catalog()  # old-style entry-point

        # Build search parameters
        search_params = catalog.construct_search_parameters(
            collections=["sentinel-2"],
            geometry=geometry,
            start_date=date_of_interest,
            end_date=date_of_interest,
            max_cloudcover=100,
            limit=10
        )
        logging.debug(f"search_params = {search_params!r}")  # inspect full params
        logging.info("Running catalog.search()")  # about to hit API

        search_results_df = catalog.search(search_params)
        logging.info(f"Search returned {len(search_results_df)} rows")  # actual row count

        if search_results_df.empty:
            logging.info("No images found; exiting.")  # nothing to do
            return

        # ––––– for testing, limit to first 2 –––––
        search_results_df = search_results_df.head(2)
        logging.info(f"Limiting to {len(search_results_df)} test images")  # test cap

        # before parallel execution
        logging.info(f"Launching {len(search_results_df)} orders with {ORDER_WORKERS} workers")  # concurrency

        with concurrent.futures.ThreadPoolExecutor(max_workers=ORDER_WORKERS) as executor:
            futures = [
                executor.submit(
                    process_order,
                    row.id,
                    geometry,
                    INPUT_PATH,
                    catalog
                )
                for row in search_results_df.itertuples()
            ]

            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                res = future.result()
                logging.info(f"Progress: {idx}/{len(futures)} → {res}")  # per-order summary

        logging.info("All orders have been processed")  # done

    except Exception:
        logging.exception("Error in download_from_up42")  # full stack on top failure
        raise


if __name__ == "__main__":
    if not CONFIG_PATH:
        logging.error("CONFIG_PATH must be set as environment variable")
        exit(1)

    if not INPUT_PATH:
        logging.error("INPUT_PATH must be set as environment variable")
        exit(1)

    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Config file not found at {CONFIG_PATH}")
        exit(1)

    download_from_up42(CONFIG_PATH)
