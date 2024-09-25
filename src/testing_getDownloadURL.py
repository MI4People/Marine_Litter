import ee
import requests
from datetime import date
import json
import os

# Define a update_json function
def update_json(filename, new_data):
    # Check if file exists
    if os.path.exists(filename):
        # Read existing data
        with open(filename, 'r') as file:
            data = json.load(file)
    else:
        # Create an empty dictionary if file doesn't exist
        data = {}

    # Update data with new values
    data.update(new_data)

    # Write updated data back to file
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

# Initialize the Earth Engine module
ee.Initialize(project='mi4people')

# Define the coordinates
coordinates = [
    [15.186692656701162,44.07373482271516],
    [15.2052320854121,44.07373482271516],
    [15.2052320854121,44.0876693925411],
    [15.186692656701162,44.0876693925411],
    [15.186692656701162,44.07373482271516]
]

# Create a polygon from the coordinates
aoi = ee.Geometry.Polygon(coordinates)

# Get the Sentinel-2 surface reflectance collection
s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')

# Filter the collection
filtered = s2_collection.filterBounds(aoi) \
    .filterDate('2019-08-01', '2019-08-31') \
    .sort('system:time_start', False) \
    .first()

image_id = filtered.get('system:index').getInfo()
print("image_id: ",image_id)

all_bands = filtered.bandNames()

# Select the RGB bands and scale them
# rgb = filtered.select(all_bands) \
#     .multiply(1) \
#     .clip(aoi)


# Set the export parameters
export_params = {
    'image': filtered.select(all_bands),
    'scale': 20,
    'region': aoi,
    'crs': 'EPSG:4326',
    'fileFormat': 'GeoTIFF',
    'fileNamePrefix': image_id,
    'filePerBand': False
}

new_json_data = {f"{date.today()}": image_id}

try:
    update_json("data.json", new_json_data)
    print(f"Data successfully updated in data.json")
except Exception as e:
    print(f"An error occurred: {e}")

# Get the download URL
url = filtered.getDownloadURL(export_params)

print(f"Download URL: {url}")

# Download the image
response = requests.get(url)
if response.status_code == 200:
    # The Download URL generates a Zip-File containing tiff-files of every single band selected
    with open(f"{image_id}.tif", "wb") as f:
        f.write(response.content)
    print(f"Image downloaded successfully as {image_id}.tif")
else:
    print(f"Failed to download image. Status code: {response.status_code}")


