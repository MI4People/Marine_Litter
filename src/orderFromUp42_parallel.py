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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DAYBEFORE     = int(os.environ.get("DAYBEFORE", 2))
CONFIG_PATH   = os.getenv("CONFIG_PATH")
INPUT_PATH    = os.getenv("INPUT_PATH")
UP42_CRED_PATH= os.getenv("UP42_CRED_PATH")
ORDER_WORKERS = int(os.environ.get("ORDER_WORKERS", 3))


def process_order(image_id: str, geometry: dict, input_path: str, catalog) -> dict:
    """
    Place an order via catalog.place_order(), wait for fulfillment,
    then download each asset via asset.file.download(...).
    """
    try:
        logging.info(f"Processing order for image {image_id}")

        # 1) Build and place order
        order_params = catalog.construct_order_parameters(
            data_product_id=PRODUCT_ID,
            image_id=image_id,
            aoi=geometry,
        )
        order = catalog.place_order(order_params)
        order_id = order.order_id  # old‐style attribute
        logging.info(f"Order {order_id} placed for image {image_id}")

        # 2) Poll until FULFILLED or FAILED
        while order.status not in ("FULFILLED", "FAILED"):
            time.sleep(60)
            order.track_status(report_time=60)
            logging.info(f"Order {order_id} status: {order.status}")

        if order.status == "FAILED":
            logging.error(f"Order {order_id} failed")
            return {
                "order_id": order_id,
                "image_id": image_id,
                "status": "FAILED",
                "assets_processed": 0
            }

        # 3) Download assets (if any)
        assets = order.get_assets()
        logging.info(f"Order {order_id} fulfilled with {len(assets)} assets")
        if not assets:
            return {
                "order_id": order_id,
                "image_id": image_id,
                "status": "FULFILLED",
                "assets_processed": 0
            }

        os.makedirs(input_path, exist_ok=True)
        assets_processed = 0

        # Silence tqdm (if used internally)
        logging.getLogger("tqdm").setLevel(logging.ERROR)

        for asset in assets:
            try:
                asset.file.download(input_path)
                logging.info(f"Asset {asset.asset_id or asset.file.id} downloaded for order {order_id}")
                assets_processed += 1

            except Exception as e:
                logging.error(f"Error downloading asset {asset.asset_id or asset.file.id} for order {order_id}: {e}")

        # (Optional) If you want to process zips immediately, uncomment:
        # for fname in os.listdir(input_path):
        #     if fname.endswith(".zip"):
        #         try:
        #             process_zip(os.path.join(input_path, fname))
        #             logging.info(f"Processed zip {fname} for order {order_id}")
        #         except Exception as e:
        #             logging.error(f"Error processing {fname} for order {order_id}: {e}")

        return {
            "order_id": order_id,
            "image_id": image_id,
            "status": "FULFILLED",
            "assets_processed": assets_processed
        }

    except Exception as e:
        logging.error(f"Error in process_order for {image_id}: {e}")
        return {
            "image_id": image_id,
            "status": "ERROR",
            "error": str(e),
            "assets_processed": 0
        }


def download_from_up42(config_path):
    """
    Authenticate → search with catalog.construct_search_parameters →
    place orders in parallel → download assets.
    """
    try:
        if not os.path.exists(UP42_CRED_PATH):
            raise FileNotFoundError(f"Credentials file not found at {UP42_CRED_PATH}")

        with open(UP42_CRED_PATH) as f:
            creds = json.load(f)

        up42.authenticate(username=creds["username"], password=creds["password"])
        logging.info("Successfully authenticated with UP42")

        # Load configuration (GeoJSON, product_id)
        with open(config_path) as f:
            config = json.load(f)

        geom = config["features"][0]["geometry"]
        geometry = {"type": geom["type"], "coordinates": geom["coordinates"]}
        global PRODUCT_ID
        PRODUCT_ID = config.get("product_id", "c3de9ed8-f6e5-4bb5-a157-f6430ba756da")

        date_of_interest = (date.today() - timedelta(days=DAYBEFORE)).strftime("%Y-%m-%d")
        logging.info(f"Date of interest is: {date_of_interest}")

        # Initialize the old-style catalog entry-point
        catalog = up42.initialize_catalog()  # DeprecationWarning: but still present

        # Build search parameters and run search
        search_params = catalog.construct_search_parameters(
            collections=["sentinel-2"],
            geometry=geometry,
            start_date=date_of_interest,
            end_date=date_of_interest,
            max_cloudcover=100,
            limit=10
        )
        search_results_df = catalog.search(search_params)
        logging.info(f"Found {len(search_results_df)} images matching criteria")

        if search_results_df.empty:
            logging.info("No images found; exiting.")
            return

        # –––––––––––––––––––––––––––––––––––––––––––––––––––
        # only keep the first 2 rows for testing:
        search_results_df = search_results_df.head(2)
        logging.info(f"Limiting to {len(search_results_df)} test images")
        # –––––––––––––––––––––––––––––––––––––––––––––––––––

        # Launch each process_order(...) in parallel, passing `catalog` as last arg
        with concurrent.futures.ThreadPoolExecutor(max_workers=ORDER_WORKERS) as executor:
            futures = [
                executor.submit(
                    process_order,
                    row.id,        # image_id
                    geometry,      # geometry
                    INPUT_PATH,    # input_path
                    catalog        # old-style catalog
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
