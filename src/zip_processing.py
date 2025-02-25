import os
import zipfile
import glob
import json
import shutil
from osgeo import gdal

def process_zip(zip_path, json_path):
    # Extract ZIP file
    extract_dir = os.path.splitext(zip_path)[0]
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Find .tif files that start with "B"
    tif_files = sorted(glob.glob(os.path.join(extract_dir, 'B*.tif')))
    if not tif_files:
        raise ValueError("No .tif files starting with 'B' found in the extracted ZIP.")

    # Extract metadata for naming convention
    metadata_file = os.path.join(extract_dir, 'metadata.xml')
    if not os.path.exists(metadata_file):
        raise FileNotFoundError("metadata.xml not found in extracted files.")

    with open(metadata_file, 'r') as meta:
        metadata_content = meta.read()
        start_tag = '<TILE_ID metadataLevel="Brief">'
        end_tag = '</TILE_ID>'
        start_index = metadata_content.find(start_tag) + len(start_tag)
        end_index = metadata_content.find(end_tag, start_index)
        if start_index == -1 or end_index == -1:
            raise ValueError("TILE_ID not found in metadata.xml")
        tile_id = metadata_content[start_index:end_index].strip()

    # Define output filename
    output_filename = f"{tile_id}.tif"
    output_path = os.path.join(os.path.dirname(zip_path), output_filename)

    # Use GDAL to merge bands into one file
    vrt_options = gdal.BuildVRTOptions(separate=True, srcNodata=0, VRTNodata=0)
    vrt_filename = output_path.replace('.tif', '.vrt')
    
    gdal.BuildVRT(vrt_filename, tif_files, options=vrt_options)

    # Convert to final GeoTIFF with scaling and NoData handling
    gdal.Translate(output_path, vrt_filename, format='GTiff',
                   scaleParams=[[0, 10000, 0, 255]],  # Rescale brightness
                   outputType=gdal.GDT_Byte,         # Ensure Byte (0-255)
                   noData=0)                         # Preserve NoData

    # Cleanup extracted files, intermediate VRT, and ZIP file
    shutil.rmtree(extract_dir, ignore_errors=True)  # Delete extracted folder
    os.remove(zip_path)  # Delete ZIP file
    os.remove(vrt_filename)  # Delete intermediate VRT file

    # Update JSON file with yesterday's date and merged filename.
    import datetime
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            json_data = json.load(json_file)
    else:
        json_data = {}
    
    if yesterday in json_data:
        json_data[yesterday].append(output_filename)
    else:
        json_data[yesterday] = [output_filename]
    
    with open(json_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)
    
    print(f"Processing complete. Output file: {output_filename}")
    print(f"JSON file updated with {output_filename} for {yesterday}")