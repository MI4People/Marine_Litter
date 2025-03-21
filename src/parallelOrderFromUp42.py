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

def place_order(catalog, order_parameters):
    return  catalog.place_order(order_parameters)

def get_all_orders():
    return up42.orders.list()

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

def download_all_assets(output_directory):
    try: 
        orders = get_all_orders()
        all_assets = []

        for order in orders:
            print(f"Processing order: {order['id']}")
            if order.status == "FULFILLED":
               assets = order.get_assets()       
               all_assets.append(assets)
    
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for asset in all_assets:
                futures.append(executor.submit(download_asset, asset, output_directory))
            show_progress(futures)

    except Exception as e:
        print(f"Error retrieving or downloading assets: {e}")
