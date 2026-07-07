import logging
import os
from argparse import ArgumentParser, HelpFormatter, Namespace
from pathlib import Path
from typing import Literal

import download_from_up42
import predict_litter
import upload_to_gc_storage
from osgeo import gdal
from torch import cuda, version

from marine_litter.ml_settings import MLSettings

log = logging.getLogger(__name__)


def main(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "WARNING", dry_run: bool = False
) -> None:
    env_file = ".env" if Path(".env").is_file() else None
    settings = MLSettings(env_file)
    settings.log_level = log_level.upper()

    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    log.info(f"Settings:\n{settings.as_table(description=dry_run)}")
    log.info(f"GDAL: {gdal.__version__}")
    if cuda.is_available():
        log.info(f"CUDA: {version.cuda}")
        for i in range(cuda.device_count()):
            p = cuda.get_device_properties(i)
            n_mp = p.multi_processor_count
            vram = p.total_memory  # bytes
            log.info(f"  {i + 1:02}: {cuda.get_device_name(i)} ({n_mp} MPs, {round(vram / 2**20)} MB)")
    else:
        log.warning("CUDA is not available!")

    log.info(10 * "=" + " Starting workflow")

    download_from_up42.main(settings, dry_run=dry_run)
    predict_litter.main(settings, dry_run=dry_run)
    upload_to_gc_storage.main(settings, dry_run=dry_run)

    log.info(10 * "=" + " Workflow completed")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])

    ap = ArgumentParser(description=__doc__, formatter_class=lambda prog: HelpFormatter(prog, max_help_position=40))
    ap.add_argument("-l", "--log", default="INFO", help="DEBUG, INFO, WARNING, ERROR, CRITICAL, default: INFO")
    ap.add_argument("-d", "--dry-run", action="store_true", help="only tell settings and do some checks")
    args: Namespace = ap.parse_args()

    main(args.log, args.dry_run)
