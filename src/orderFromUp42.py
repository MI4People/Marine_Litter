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

logging.basicConfig(level=logging.INFO)

DAYBEFORE = int(os.environ.get("DAYBEFORE", 2))
CONFIG_PATH = os.getenv("CONFIG_PATH")
INPUT_PATH = os.getenv("INPUT_PATH")
UP42_CRED_PATH = os.getenv("UP42_CRED_PATH")

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

def download_from_up42(config_path):
    """Main function to authenticate, search, and download assets from UP42."""
    # Authenticate with UP42
    if not os.path.exists(UP42_CRED_PATH):
        raise FileNotFoundError(f"Credentials file not found at {UP42_CRED_PATH}")

    with open(UP42_CRED_PATH, "r") as credentials_file:
        credentials = json.load(credentials_file)

    up42.authenticate(username=credentials["username"], password=credentials["password"])
    logging.info("Successfully authenticated with UP42.")

    # Load configuration
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # Geojson information storing
    coordinate_type = config["features"][0]["geometry"]["type"]
    coordinates = config["features"][0]["geometry"]["coordinates"]
    
    product_id = config.get("product_id", "c3de9ed8-f6e5-4bb5-a157-f6430ba756da")
    logging.info("type is: ", config["features"][0]["geometry"]["type"])
    
    # Initialize catalog and search for images
    catalog = up42.initialize_catalog()
    geometry = {
        "type": coordinate_type,
        "coordinates": coordinates,
    }
    
    date_of_interest = (date.today() - timedelta(days=DAYBEFORE)).strftime("%Y-%m-%d")
    print("Date of interest is: ", date_of_interest)
    
    search_parameters = catalog.construct_search_parameters(
        collections=["sentinel-2"],
        geometry=geometry,
        start_date=date_of_interest,
        end_date=date_of_interest,
        max_cloudcover=20,
    )
    
    search_results_df = catalog.search(search_parameters)
    print(search_results_df)

    if search_results_df.empty:
        logging.info("No images found for the given date range and parameters.")
        return

    # Place order and download assets
    for index, _ in search_results_df.iterrows():
        print(index)
        order_parameters = catalog.construct_order_parameters(
            data_product_id=product_id,
            image_id=search_results_df.iloc[index]["id"],
            aoi=geometry,
        )

        # in_ = input("Do you want to place order? (y/n): ")
        order = catalog.place_order(order_parameters)

        # This is a quick hack to test order fulfillment and downloading order as soon as it is fulfilled
        # We get a console output status report every 120 seconds
        print(order.track_status(report_time=120))
        while(order.is_fulfilled == False):
            time.sleep(120)
            
        if order.status == "FULFILLED":
            assets = order.get_assets()
            print("--before assets download attempt--")
            
            for asset in assets:
                asset.download(
                INPUT_PATH,
                unpacking=False,
            )
            
            print("--after assets download attempt--")
            if not assets:
                logging.info("No assets found in the order.")
                return

            for file in os.listdir(INPUT_PATH):
                if file.endswith(".zip"):
                    zip_file_path = os.path.join(INPUT_PATH, file)
                    try:
                        process_zip(zip_file_path)
                        logging.info(f"Successfully processed {file}")
                    except Exception as e:
                        logging.error(f"Error processing {file}: {e}")        

            print("--starting concurrent jobs--")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(download_asset, asset, INPUT_PATH) for asset in assets]
                show_progress(futures)

            logging.info("\nAll assets have been downloaded.")

if __name__ == "__main__":
    if not CONFIG_PATH:
        logging.error("CONFIG_PATH must be set as environment variables.")
        exit(1)

    if not os.path.exists(CONFIG_PATH):
        logging.error(f"Config file not found at {CONFIG_PATH}")
        exit(1)

    # Run the download process
    download_from_up42(CONFIG_PATH)