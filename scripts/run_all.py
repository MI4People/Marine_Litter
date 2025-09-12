import logging
from argparse import ArgumentParser, BooleanOptionalAction, HelpFormatter, Namespace

from convert import run_convert
from prediction import run_prediction
from up42_order_and_download import run_order_and_download_from_up42
from upload_delete import run_upload_delete

from marine_litter.ml_settings import MLSettings

logg = logging.getLogger(__name__)


def run_all():
    ap = ArgumentParser(description=__doc__, formatter_class=lambda prog: HelpFormatter(prog, max_help_position=40))
    ap.add_argument("-l", "--log", default="INFO", help="DEBUG, INFO, WARNING, ERROR, CRITICAL, default: INFO")
    ap.add_argument("-d", "--dry-run", action=BooleanOptionalAction, default=False, help="just echo command")
    args: Namespace = ap.parse_args()

    settings = MLSettings()
    settings.log_level = args.log
    logging.basicConfig(level=settings.log_level, format=settings.log_format)

    logging.info(10 * "=" + " Starting workflow")
    if args.dry_run:
        logging.info(f"dry run with settings:\n{settings}")
    else:
        run_order_and_download_from_up42(settings)
        run_prediction(settings)
        run_convert(settings)
        run_upload_delete(settings)
    logging.info(10 * "=" + " Workflow completed")


if __name__ == "__main__":
    run_all()
