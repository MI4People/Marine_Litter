"""See also
- https://github.com/up42/up42-py/
- https://docs.up42.com/sdk/quick-start
"""

import asyncio
import json
import logging
import os
import sys
from argparse import ArgumentParser, HelpFormatter, Namespace
from collections import defaultdict
from collections.abc import ValuesView
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import geojson
from geojson import FeatureCollection
from pystac import Asset

# ML-002: Use official UP42 env var to disable version check instead of MagicMock hack
os.environ.setdefault("UP42_DISABLE_VERSION_CHECK", "true")

from up42 import Order, authenticate, stac_client, utils  # noqa: E402
from up42.glossary import Collection, CollectionSorting, CollectionType, ProductGlossary, Provider, Scene  # noqa: E402
from up42.order_template import BatchOrderTemplate, OrderError, OrderReference  # noqa: E402

# ML-003: Configure UP42 loggers to propagate to root instead of monkey-patching
# First, configure the root "up42" logger so all children inherit propagation
_up42_root_logger = logging.getLogger("up42")
_up42_root_logger.handlers.clear()
_up42_root_logger.propagate = True
# Belt-and-suspenders: also clear handlers on any child loggers already created at import time
for _logger_name in logging.Logger.manager.loggerDict:
    if _logger_name.startswith("up42"):
        _logger_obj = logging.getLogger(_logger_name)
        if isinstance(_logger_obj, logging.Logger):
            _logger_obj.propagate = True
            _logger_obj.handlers.clear()

from marine_litter.ml_settings import MLSettings

log = logging.getLogger(__name__)

DEFAULT_POLLING_TO = 20 * 60.0  # polling for order fulfillment timeout

# Terminal failure states in UP42 v3.4.0 (OrderStatus is a Literal type, not an enum)
ORDER_TERMINAL_FAILURE_STATES = frozenset({"FAILED_PERMANENTLY", "CANCELED", "PLACEMENT_FAILED"})


@dataclass
class ProductInfo:
    """Collect information of 3 classes when looking through UP42 collections."""

    collection_name: str
    product_id: str
    product_name: str
    host: Provider


@dataclass
class SceneSearchParams:
    """Criteria for searching scenes in UP42. `Scene`: several TIFFs in a zip file then."""

    collection_name: str
    polygon: geojson.Polygon
    start_date: str
    end_date: str
    clouds_perc_max: int


def authenticate_with_up42(up42_creds_path: Path) -> bool:
    """:returns: success."""
    try:
        with up42_creds_path.open(encoding="utf-8") as f:
            creds = json.load(f)
    except (OSError, TypeError, json.JSONDecodeError) as e:
        log.error(f"Failed to load credentials: {e}")
        return False
    try:
        authenticate(username=creds.get("username"), password=creds.get("password"))  # logs itself
    except ValueError as e:
        log.error(f"Failed to authenticate: {e}")
        return False
    return True


def fetch_collections() -> list[Collection]:
    log.debug("Fetching available collections from UP42 ProductGlossary...")
    collections = list(
        ProductGlossary.get_collections(collection_type=CollectionType.ARCHIVE, sort_by=CollectionSorting.name)
    )
    if collections:
        log.debug(f"...got {len(collections)} collections.")
    else:
        log.error("...no UP42 ProductGlossary collection available.")
    return collections


def determine_product_info(product_name: str) -> ProductInfo | None:
    log.info(f"Determine product info for '{product_name}'.")
    product_info: ProductInfo | None = None
    collections = fetch_collections()
    if collections:
        # log.setLevel(logging.DEBUG)  # to see available collections and their data products
        for i, collection in enumerate(collections, 1):
            log.debug(f"{i:02}. {collection.title}")
            for dp in collection.data_products:
                log.debug(f"    {dp.name}: {dp.id}")
                if dp.name == product_name and dp.id:
                    # assert collection.title == 'Sentinel-2'
                    # assert collection.name == 'sentinel-2'
                    # assert dp.title == 'Level 2A'
                    host = next(p for p in collection.providers if p.is_host)
                    product_info = ProductInfo(collection.name, dp.id, dp.name, host=host)
    if product_info is None:
        log.error(f"No provider for '{product_name}' found.")
    return product_info


def determine_scenes(host, params: SceneSearchParams) -> list[Scene]:
    one_or_two_dates = f"{params.start_date}"
    if params.start_date != params.end_date:
        one_or_two_dates += f"...{params.end_date}"
    log.info(f"Searching for scenes of {one_or_two_dates}.")
    scenes = list(
        host.search(
            collections=[params.collection_name],
            intersects=params.polygon,
            start_date=params.start_date,
            end_date=params.end_date,
            query={"cloudCoverage": {"LT": params.clouds_perc_max}},
        )
    )
    if not scenes:
        log.warning("...no scene found.")
    else:
        scenes_by_date = defaultdict(list)
        for i, scene in enumerate(scenes, 1):
            # not sure datetime is always set, but we need unique keys
            s_date: str = scene.datetime[:10] if scene.datetime else f"? {i:8}"
            scenes_by_date[s_date].append(scene)

        log_lines = [f"Found {len(scenes)} scene(s)."]
        for s_date in sorted(scenes_by_date):
            l_scenes = scenes_by_date[s_date]
            log_lines.append(f"  {s_date} ({len(l_scenes)}):")
            for i, scene in enumerate(sorted(l_scenes, key=lambda sc: sc.datetime or ""), 1):
                time_str = scene.datetime[11:19] if scene.datetime else f"? {i:6}"
                cloud_str = f"{scene.cloud_coverage:5.1f}" if scene.cloud_coverage is not None else "  N/A"
                log_lines.append(f"    {time_str} '{scene.id}':{cloud_str}% clouds")
        log.info("\n".join(log_lines))
    return scenes


def _download_single_order(download_dir: Path, order: Order) -> bool:
    items = stac_client().search(filter={"op": "=", "args": [{"property": "order_id"}, order.id]})
    for item in items.items():
        collection = item.get_collection()
        if not collection:
            continue
        assets: ValuesView[Asset] = collection.assets.values()
        order_asset = next((asset for asset in assets if asset.roles and "original" in asset.roles), None)
        if order_asset:  # aka `original_delivery`
            downloaded_file_path = order_asset.file.download(output_directory=download_dir)  # noqa logs itself
            log.debug(f"Downloaded '{downloaded_file_path}' for order {order.id}.")
            return True
    log.error(f"Asset not found for order {order.id}.")
    return False


async def _process_single_order(scene_id: str, order: Order, download_dir: Path, poll_timeout_secs) -> bool:
    """Process a single order: poll until fulfilled (or failed), then download assets.
    :returns: success.
    """
    try:
        start_time = datetime.now()
        timed_out = False
        while not order.is_fulfilled and order.status not in ORDER_TERMINAL_FAILURE_STATES:
            await asyncio.sleep(6.0)
            order: Order = await asyncio.to_thread(Order.get, order.id)
            order.track()
            if (datetime.now() - start_time).total_seconds() > poll_timeout_secs:
                timed_out = True
                break

        duration = datetime.now() - start_time
        if timed_out or order.status in ORDER_TERMINAL_FAILURE_STATES:
            log.error(f"Order {order.id} {order.status} after {duration}")
            return False
        log.info(f"Order {order.id} fulfilled after {duration}")

        return _download_single_order(download_dir, order)

    except Exception as e:
        log.exception(f"Error processing order {order.id} for {scene_id}: {e}")
        return False


async def process_orders_concurrently(order_by_scene_id: dict[str, Order], download_dir: Path):
    timeout = DEFAULT_POLLING_TO
    log.info(f"Processing {len(order_by_scene_id)} order(s) (timeout: {timeout / 60:.1f} min) concurrently...")
    results = await asyncio.gather(
        *[_process_single_order(sc_id, order, download_dir, timeout) for sc_id, order in order_by_scene_id.items()],
        return_exceptions=True,
    )
    failures = 0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            log.error(f"Ordering task {i} raised exception: {result}")
            failures += 1
        elif result is False:
            failures += 1
    log.info(f"...completed {len(results)} orders, {failures} failed.")
    if len(order_by_scene_id) != len(results):
        log.error(f"Order count mismatch: expected {len(order_by_scene_id)}, got {len(results)}")


def place_orders(scenes: list[Scene], product_info, features: FeatureCollection) -> dict:
    """:returns: placed orders by scene ID."""
    log.info(f"Placing {len(scenes)} order(s)...")
    order_tasks = {}
    for i, scene in enumerate(scenes, 1):
        order_template = BatchOrderTemplate(
            data_product_id=product_info.product_id,
            display_name=f"{scene.id}",
            features=features,
            params={"id": scene.id},
        )
        got: list[OrderReference | OrderError] = order_template.place()
        if got and isinstance(got[0], OrderReference):
            order: Order = got[0].order
            log.info(f"   {i}: ✓ {order.id} for scene {scene.id}")
            order_tasks[scene.id] = order
        elif got and isinstance(got[0], OrderError):
            log.error(f"  {i}: error for scene {scene.id}: {got[0]}")

    return order_tasks


def main(settings: MLSettings | None = None, dry_run=False, tell_only=False):
    """Main workflow with UP42: authenticate, search scenes, place orders, poll for scenes (images), download."""
    if settings is None:
        settings = MLSettings(".env")
        logging.basicConfig(level=settings.log_level, format=settings.log_format)
        log.info(f"Settings:\n{settings.as_table()}")

    log.info(10 * "-" + f" Download scenes (images) from UP42 {' (tell only)' if tell_only else ''}")

    # check early for `dry_run`
    date1 = date.today() - timedelta(days=settings.days_before)
    date2 = date1 + timedelta(days=settings.days_num - 1)
    with settings.geojson_path.open(encoding="utf-8") as f:
        feature_collection = geojson.FeatureCollection(json.load(f)["features"])
        polygon = geojson.Polygon(feature_collection[0]["geometry"]["coordinates"])

    if not authenticate_with_up42(settings.up42_creds_path):
        return

    if dry_run:
        return

    product_info = determine_product_info(settings.product_name)
    if not product_info:
        return

    scenes = determine_scenes(
        product_info.host,
        SceneSearchParams(
            collection_name=product_info.collection_name,
            polygon=polygon,
            start_date=date1.strftime("%Y-%m-%d"),
            end_date=date2.strftime("%Y-%m-%d"),
            clouds_perc_max=settings.clouds_perc_max,
        ),
    )
    if tell_only or not scenes:
        return

    order_tasks = place_orders(scenes, product_info, feature_collection)
    if order_tasks:
        download_dir = settings.input_path
        download_dir.mkdir(parents=True, exist_ok=True)
        asyncio.run(process_orders_concurrently(order_tasks, download_dir))


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])

    ap = ArgumentParser(description=__doc__, formatter_class=lambda prog: HelpFormatter(prog, max_help_position=40))
    ap.add_argument("-l", "--log", default="INFO", help="DEBUG, INFO, WARNING, ERROR, CRITICAL, default: INFO")
    ap.add_argument("-d", "--dry-run", action="store_true", help="just tell settings and do some checks")
    ap.add_argument("-t", "--tell-only", action="store_true", help="tell only scenes (images), do not order them")
    args: Namespace = ap.parse_args()
    env_file = ".env" if Path(".env").is_file() else None
    settings = MLSettings(env_file)
    settings.log_level = args.log

    logging.basicConfig(level=settings.log_level, format=settings.log_format)

    log.info(f"Settings:\n{settings.as_table(description=args.dry_run)}")

    main(settings, args.dry_run, args.tell_only)
