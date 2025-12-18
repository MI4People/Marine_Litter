import logging
import os
from argparse import ArgumentParser, BooleanOptionalAction, HelpFormatter, Namespace
from pathlib import Path

import download_from_up42
import predict_litter
import upload_to_gc_storage

from marine_litter.ml_settings import MLSettings

log = logging.getLogger(__name__)


def main():
    ap = ArgumentParser(description=__doc__, formatter_class=lambda prog: HelpFormatter(prog, max_help_position=40))
    ap.add_argument("-l", "--log", default="INFO", help="DEBUG, INFO, WARNING, ERROR, CRITICAL, default: INFO")
    ap.add_argument("-d", "--dry-run", action=BooleanOptionalAction, default=False, help="just echo command")
    args: Namespace = ap.parse_args()

    env_file = ".env" if Path(".env").is_file() else None
    settings = MLSettings(env_file)
    settings.log_level = args.log
    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    log.info(f"Settings:\n{settings.as_table(description=args.dry_run)}")

    log.info(10 * "=" + " Starting workflow")

    download_from_up42.main(settings, dry_run=args.dry_run)
    predict_litter.main(settings, dry_run=args.dry_run)
    upload_to_gc_storage.main(settings, dry_run=args.dry_run)

    log.info(10 * "=" + " Workflow completed")


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parents[1])
    main()
