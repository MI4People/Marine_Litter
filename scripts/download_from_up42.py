import concurrent.futures
import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from marine_litter.ml_settings import MLSettings

# To avoid network issues: disable version check when importing up42 package
#    see https://github.com/up42/up42-py/blob/master/up42/version/version_control.py
mock = MagicMock()
mock.json.return_value = {"info": {"version": "0.0.0"}}
with patch("requests.get", return_value=mock):
    import up42  # noqa: E402
    from up42 import Catalog  # noqa: E402

log = logging.getLogger(__name__)


def process_order(image_id: str, geometry: dict, input_path: Path, catalog: Catalog, product_id: str) -> dict:
    """Call catalog.place_order(), wait for fulfillment, then download each via asset.file.download()."""
    try:
        log.info(f"Processing order for image {image_id}")

        # 1) Build and place order
        order_params = catalog.construct_order_parameters(
            data_product_id=product_id,
            image_id=image_id,
            aoi=geometry,
        )
        order = catalog.place_order(order_params)
        order_id = order.order_id  # old‐style attribute
        log.info(f"Order {order_id} placed for image {image_id}")

        # 2) Poll until FULFILLED or FAILED
        while order.status not in {"FULFILLED", "FAILED"}:
            time.sleep(60)
            order.track_status(report_time=60)
            log.info(f"Order {order_id} status: {order.status}")

        if order.status == "FAILED":
            log.error(f"Order {order_id} failed")
            return {"order_id": order_id, "image_id": image_id, "status": "FAILED", "assets_processed": 0}

        # 3) Download assets (if any)
        assets = order.get_assets()
        log.info(f"Order {order_id} fulfilled with {len(assets)} assets")
        if not assets:
            return {"order_id": order_id, "image_id": image_id, "status": "FULFILLED", "assets_processed": 0}

        input_path.mkdir(parents=True, exist_ok=True)
        assets_processed = 0
        try:
            for asset in assets:
                asset.file.download(input_path)
                log.info(f"'{image_id}' downloaded for order {order_id}")
                assets_processed += 1
        except Exception as e:
            log.exception(f"Error downloading '{image_id}' for order {order_id}: {e}")

        log.info(f"Directory snapshot after downloads: {os.listdir(input_path)}")

        return {"order_id": order_id, "image_id": image_id, "status": "FULFILLED", "assets_processed": assets_processed}

    except Exception as e:
        log.exception(f"Error in process_order() for {image_id} ({e})")
        return {"image_id": image_id, "status": "ERROR", "error": "see logs", "assets_processed": 0}


def main(settings: MLSettings | None = None, dry_run: bool = False):
    """Workflow: authenticate at UP42, search, put orders, poll for images, download."""
    if settings is None:
        settings = MLSettings(".env")
        logging.basicConfig(level=settings.log_level, format=settings.log_format)
        log.info(f"Settings:\n{settings.as_table()}")

    log.info(10 * "-" + " Download images from UP42")
    try:
        up42_creds_path = settings.up42_creds_path
        config_path = settings.config_path
        if not up42_creds_path.is_file():
            raise FileNotFoundError(f"Credentials '{up42_creds_path}' not found!")
        if not config_path.is_file():
            raise FileNotFoundError(f"{MLSettings.model_fields['config_path'].description} '{config_path}' not found!")

        with up42_creds_path.open(encoding="utf-8") as f:
            creds = json.load(f)

        if dry_run:
            return

        up42.authenticate(username=creds["username"], password=creds["password"])
        log.info("Successfully authenticated with UP42")

        with config_path.open(encoding="utf-8") as f:
            config = json.load(f)

        geom = config["features"][0]["geometry"]
        geometry = {"type": geom["type"], "coordinates": geom["coordinates"]}
        product_id = config.get("product_id", settings.product_id)

        date_of_interest = (date.today() - timedelta(days=settings.days_before)).strftime("%Y-%m-%d")
        log.info(f"Date of interest is: {date_of_interest}")

        catalog = up42.initialize_catalog()
        search_params = catalog.construct_search_parameters(
            geometry=geometry,
            collections=["sentinel-2"],
            start_date=date_of_interest,
            end_date=date_of_interest,
            max_cloudcover=50,  # in percent
        )
        search_results_df = catalog.search(search_params)
        log.info(f"Found {len(search_results_df)} images matching criteria")
        if search_results_df.empty:
            log.info("No images found; exiting.")
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.order_workers) as executor:
            futures = [
                executor.submit(
                    process_order,
                    getattr(row, "id", row[1]),
                    geometry,
                    settings.input_path,
                    catalog,
                    product_id,
                )
                for row in search_results_df.itertuples()
            ]
            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                res = future.result()
                log.info(f"Progress: {idx}/{len(futures)} → {res}")

        log.info("All orders have been processed")

    except Exception as e:
        log.error(f"Error in download_from_up42: {e}")
        raise


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])
    main()
