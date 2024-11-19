import os
import json
import logging
import concurrent.futures
import time
import up42

logging.basicConfig(level=logging.INFO)

def download_asset(asset, output_directory):
    """Downloads a single asset."""
    try:
        asset_id = asset["id"]
        initialized_asset = up42.initialize_asset(asset_id=asset_id)

        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        initialized_asset.download(output_directory=output_directory, unpacking=False)
        logging.info(f"Asset {asset_id} downloaded successfully!")
    except Exception as e:
        logging.error(f"Failed to process asset {asset['id']}: {e}")

def show_progress(futures):
    """Displays download progress for assets."""
    total = len(futures)
    while True:
        done_count = sum(f.done() for f in futures)
        running_count = sum(1 for f in futures if f.running())
        print(f"Progress: {done_count}/{total} completed, {running_count} running.", end='\r')
        if done_count == total:
            break
        time.sleep(1)

def download_from_up42(date_from, date_to, config_path):
    """Main function to authenticate, search, and download assets from UP42."""
    # Authenticate with UP42
    credentials_path = "src/.up42/credentials.json"
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Credentials file not found at {credentials_path}")

    with open(credentials_path, "r") as credentials_file:
        credentials = json.load(credentials_file)

    up42.authenticate(username=credentials["username"], password=credentials["password"])
    logging.info("Successfully authenticated with UP42.")

    # Load configuration
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    coordinates = config["coordinates"]
    product_id = config.get("product_id", "c3de9ed8-f6e5-4bb5-a157-f6430ba756da")

    # Initialize catalog and search for images
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

    if search_results_df.empty:
        logging.info("No images found for the given date range and parameters.")
        return

    # Place order and download assets
    order_parameters = catalog.construct_order_parameters(
        product_id=product_id,
        image_id=search_results_df.iloc[0]["id"],
        aoi=geometry,
    )

    order = catalog.place_order(order_parameters)
    if order.status == "FULFILLED":
        assets = order.get_assets()
        if not assets:
            logging.info("No assets found in the order.")
            return

        output_directory = "src/resources/download_images"
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(download_asset, asset, output_directory) for asset in assets]
            show_progress(futures)

        logging.info("\nAll assets have been downloaded.")

if __name__ == "__main__":
    # Read environment variables
    DATE_FROM = os.getenv("DATE_FROM")
    DATE_TO = os.getenv("DATE_TO")
    CONFIG_PATH = os.getenv("CONFIG_PATH")

    if not DATE_FROM or not DATE_TO or not CONFIG_PATH:
        logging.error("DATE_FROM, DATE_TO, and CONFIG_PATH must be set as environment variables.")
        exit(1)

    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Config file not found at {CONFIG_PATH}")
        exit(1)

    # Run the download process
    download_from_up42(DATE_FROM, DATE_TO, CONFIG_PATH)
