import logging
import subprocess
from pathlib import Path

from marine_litter.ml_settings import MLSettings


def convert_images(input_folder: Path):
    input_folder = Path(input_folder)
    for file_name in input_folder.iterdir():
        if file_name.name.endswith("_prediction.tif"):
            input_file = file_name
            temp_file = input_folder / f"temp_{file_name.name}"
            command = f"gdal_translate {input_file} {temp_file} -co TILED=YES -co COPY_SRC_OVERVIEWS=YES"
            try:
                logging.info(f"Processing file: {input_file}")
                subprocess.run(command, shell=True, check=True)
                temp_file.replace(input_file)
                logging.info(f"Successfully converted: {file_name.name}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Error converting file {file_name.name}: {e}")
                if temp_file.exists():
                    temp_file.unlink()


def run_convert(settings: MLSettings = None):
    if settings is None:
        settings = MLSettings()
    logging.basicConfig(level=settings.log_level, format=settings.log_format)
    logging.info(10 * "-" + " Convert images")

    output_path = Path(settings.output_path)
    if not output_path.exists():
        logging.error(f"Output folder {output_path} does not exist.")
    else:
        convert_images(output_path)


if __name__ == "__main__":
    run_convert()
