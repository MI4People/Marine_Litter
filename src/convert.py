import os
import subprocess
import logging
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def convert_images(input_folder):
    """Convert all TIFF images in the input folder using gdal_translate."""
    for file_name in os.listdir(input_folder):
        if file_name.endswith("_prediction.tif"):
            input_file = os.path.join(input_folder, file_name)

            temp_file = os.path.join(input_folder, f"temp_{file_name}")

            command = f"gdal_translate {input_file} {temp_file} -co TILED=YES -co COPY_SRC_OVERVIEWS=YES"
            try:
                logging.info(f"Processing file: {input_file}")
                subprocess.run(command, shell=True, check=True)
                
                os.replace(temp_file, input_file)

                logging.info(f"Successfully converted: {file_name}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Error converting file {file_name}: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file) 

if __name__ == "__main__":
    output_folder = "images/predicted"
    if not os.path.exists(output_folder):
        logging.error(f"Output folder {output_folder} does not exist.")
    else:
        convert_images(output_folder)
