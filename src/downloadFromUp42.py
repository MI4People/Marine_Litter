import logging
import os
import up42
import json
import concurrent.futures
import time
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from environment variables or files
config_path = os.getenv("CONFIG_PATH", "src/resources/coordinates.json")
date_from = os.getenv("DATE_FROM")
date_to = os.getenv("DATE_TO")

if not date_from or not date_to:
    logging.error("Both DATE_FROM and DATE_TO environment variables must be set.")
    sys.exit(1)

# Load the coordinates from config.json
with open(config_path, "r") as file:
    config = json.load(file)

coordinates = config["coordinates"]
product_id = "c3de9ed8-f6e5-4bb5-a157-f6430ba756da"

def download_asset(asset):
    """Download the asset from UP42."""
    try:
        asset_id = asset["id"]
        initialized_asset = up42.initialize_asset(asset_id=asset_id)
        
        # Define output directory
        output_directory = "src/resources/download_images"
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        # Download the asset
        initialized_asset.download(output_directory=output_directory, unpacking=False)
        logging.info(f"Asset {asset_id} downloaded successfully!")
    
    except Exception as e:
        logging.error(f"Failed to process asset {asset['id']}: {e}")

def show_progress(futures):
    """Show progress of parallel downloads."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        logging.info(f"Progress: {done_count}/{total} completed, {running_count} running.", end='\r')
        
        if done_count == total:
            break
        
        time.sleep(1)

def download_from_up42(date_from, date_to):
    """Download assets from UP42 using the provided date range."""
    up42.authenticate(cfg_file="src/.up42/credentials.json")
    catalog = up42.initialize_catalog()
    geometry = {
        "type": "Polygon",
        "coordinates": coordinates,
    }

    search_parameters = catalog.construct_search_parameters(
        collections=["sentinel-2"],
        geometry=geometry,
        start_date=date_from,
        end_date=date_to,
        max_cloudcover=20,
    )
    search_results_df = catalog.search(search_parameters)
    
    order_parameters = catalog.construct_order_parameters(
        product_id=product_id,
        image_id=search_results_df.iloc[0]["id"],
        aoi=geometry,
    )

    order_estimate = catalog.estimate_order(order_parameters)
    logging.info(order_estimate)

    order = catalog.place_order(order_parameters)
    order_id = order["id"]

    if order.status == "FULFILLED":
        assets = order.get_assets()
        if not assets:
            logging.info("No assets found in the order.")
            return

        # Download assets in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(download_asset, asset) for asset in assets]
            show_progress(futures)

        logging.info("\nAll assets have been downloaded.")
    else:
        logging.error("Order was not fulfilled successfully.")

# Run the download
download_from_up42(date_from, date_to)
