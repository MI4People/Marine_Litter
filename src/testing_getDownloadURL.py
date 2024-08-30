import ee
import requests
import os

# Initialize the Earth Engine module
ee.Initialize(project='mi4people')

# Define the coordinates
coordinates = [
    [-122.4481, 37.7599],
    [-122.5012, 37.7324],
    [-122.5391, 37.7071],
    [-122.4904, 37.6887],
    [-122.4376, 37.7228]
]

# Create a polygon from the coordinates
aoi = ee.Geometry.Polygon(coordinates)

# Get the Sentinel-2 surface reflectance collection
s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')

# Filter the collection
filtered = s2_collection.filterBounds(aoi) \
    .filterDate('2019-07-15', '2019-07-20') \
    .sort('CLOUDY_PIXEL_PERCENTAGE') \
    .first()

# Select the RGB bands and scale them
rgb = filtered.select(['B4', 'B3', 'B2']) \
    .multiply(0.0001) \
    .clip(aoi)

# Set visualization parameters
vis_params = {
    'min': 0,
    'max': 0.3,
    'bands': ['B4', 'B3', 'B2']
}

# Set the export parameters
export_params = {
    'scale': 10,
    'region': aoi,
    'crs': 'EPSG:4326',
    'fileFormat': 'GeoTIFF'
}

# Get the download URL
url = rgb.getDownloadURL(export_params)

print(f"Download URL: {url}")

# Download the image
response = requests.get(url)
if response.status_code == 200:
    # The Download URL generates a Zip-File containing tiff-files of every single band selected
    with open("sentinel2_rgb.zip", "wb") as f:
        f.write(response.content)
    print("Image downloaded successfully as sentinel2_rgb.zip")
else:
    print(f"Failed to download image. Status code: {response.status_code}")