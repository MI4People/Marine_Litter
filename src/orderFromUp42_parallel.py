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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DAYBEFORE = int(os.environ.get("DAYBEFORE", 2))
CONFIG_PATH = os.getenv("CONFIG_PATH")
INPUT_PATH = os.getenv("INPUT_PATH")
UP42_CRED_PATH = os.getenv("UP42_CRED_PATH")
ORDER_WORKERS = int(os.environ.get("ORDER_WORKERS", 3))

def process_order(image_id, product_id, geometry, input_path):
    """
    Process a single order: place order, track status, download and process assets.
    Returns result information.
    """
    try:
        logging.info(f"Processing order for image {image_id}")
        
        # Initialize catalog for each thread to avoid potential thread safety issues
        catalog = up42.initialize_catalog()
        
        # Construct order parameters
        order_parameters = catalog.construct_order_parameters(
            data_product_id=product_id,
            image_id=image_id,
            aoi=geometry,
        )
        
        # Place the order
        order = catalog.place_order(order_parameters)
        order_id = order.order_id
        logging.info(f"Order {order_id} placed for image {image_id}")
        
        # Track order status
        while not order.is_fulfilled:
            status = order.track_status(report_time=60)  # Reduced from 120s to 60s
            logging.info(f"Order {order_id} status: {order.status}")
            if order.status == "FAILED":
                logging.error(f"Order {order_id} failed")
                return {
                    "order_id": order_id,
                    "image_id": image_id,
                    "status": "FAILED",
                    "assets_processed": 0
                }
            time.sleep(60)  # Reduced wait time
        
        # Order fulfilled, download assets
        if order.status == "FULFILLED":
            assets = order.get_assets()
            logging.info(f"Order {order_id} fulfilled with {len(assets)} assets")
            
            if not assets:
                logging.warning(f"No assets found for order {order_id}")
                return {
                    "order_id": order_id,
                    "image_id": image_id,
                    "status": "FULFILLED",
                    "assets_processed": 0
                }
                
            assets_processed = 0
            # Download and process assets
            for asset in assets:
                try:
                    # Make sure output directory exists
                    if not os.path.exists(input_path):
                        os.makedirs(input_path)
                    
                    # Download asset
                    asset.download(input_path, unpacking=False)
                    logging.info(f"Asset {asset['id']} downloaded for order {order_id}")
                    assets_processed += 1
                except Exception as e:
                    logging.error(f"Error downloading asset {asset['id']} for order {order_id}: {e}")
            
            # Process downloaded zip files
            for file in os.listdir(input_path):
                if file.endswith(".zip"):
                    zip_file_path = os.path.join(input_path, file)
                    try:
                        process_zip(zip_file_path)
                        logging.info(f"Successfully processed {file} for order {order_id}")
                    except Exception as e:
                        logging.error(f"Error processing {file} for order {order_id}: {e}")
            
            return {
                "order_id": order_id,
                "image_id": image_id,
                "status": "FULFILLED",
                "assets_processed": assets_processed
            }
    except Exception as e:
        logging.error(f"Error processing order for image {image_id}: {e}")
        return {
            "image_id": image_id,
            "status": "ERROR",
            "error": str(e),
            "assets_processed": 0
        }

def download_from_up42(config_path):
    """Main function to authenticate, search, and parallel process orders from UP42."""
    try:
        # Authenticate with UP42
        if not os.path.exists(UP42_CRED_PATH):
            raise FileNotFoundError(f"Credentials file not found at {UP42_CRED_PATH}")

        with open(UP42_CRED_PATH, "r") as credentials_file:
            credentials = json.load(credentials_file)

        up42.authenticate(username=credentials["username"], password=credentials["password"])
        logging.info("Successfully authenticated with UP42")

        # Load configuration
        with open(config_path, "r") as config_file:
            config = json.load(config_file)

        # Extract geojson information
        coordinate_type = config["features"][0]["geometry"]["type"]
        coordinates = config["features"][0]["geometry"]["coordinates"]
        product_id = config.get("product_id", "c3de9ed8-f6e5-4bb5-a157-f6430ba756da")
        
        # Prepare geometry
        geometry = {
            "type": coordinate_type,
            "coordinates": coordinates,
        }
        
        # Calculate date of interest
        date_of_interest = (date.today() - timedelta(days=DAYBEFORE)).strftime("%Y-%m-%d")
        logging.info(f"Date of interest is: {date_of_interest}")
        
        # Initialize catalog and search for images
        catalog = up42.initialize_catalog()
        search_parameters = catalog.construct_search_parameters(
            collections=["sentinel-2"],
            geometry=geometry,
            start_date=date_of_interest,
            end_date=date_of_interest,
            max_cloudcover=20,
        )
        
        search_results_df = catalog.search(search_parameters)
        logging.info(f"Found {len(search_results_df)} images matching criteria")

        if search_results_df.empty:
            logging.info("No images found for the given date range and parameters")
            return

        # Process orders in parallel
        logging.info(f"Starting parallel processing of {len(search_results_df)} orders with {ORDER_WORKERS} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=ORDER_WORKERS) as executor:
            # Create a list of futures for each image to process
            futures = [
                executor.submit(
                    process_order, 
                    search_results_df.iloc[index]["id"], 
                    product_id, 
                    geometry, 
                    INPUT_PATH
                ) 
                for index in range(len(search_results_df))
            ]
            
            # Show progress as orders complete
            completed = 0
            total = len(futures)
            
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                result = future.result()
                logging.info(f"Progress: {completed}/{total} orders completed")
                logging.info(f"Order result: {result}")
        
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

    # Run the download process
    download_from_up42(CONFIG_PATH)
    
