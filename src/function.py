import ee
import json 

# Reading JSON from a file
with open('coordinates.json', 'r') as file:
    data = json.load(file)

ee.Authenticate()

# Initialize Earth Engine
ee.Initialize()
print("Earth Engine is initialized.")

print(ee.String('Hello from the Earth Engine servers!').getInfo())
# Test with a simple Earth Engine operation
image = ee.Image('srtm90_v4')
print(image.getInfo())

coordinates = data['features'][0]['geometry']['coordinates']
aoi = ee.Geometry.Polygon(coordinates)

# Filter Sentinel-2 Surface Reflectance image collection for given date range and area.
collection = (ee.ImageCollection('COPERNICUS/S2_SR')
              .filterDate('2019-07-15', '2019-07-20')
              .filterBounds(aoi)
              .first())

true_color_image = collection.normalizedDifference(['B4', 'B3', 'B2']).rename('True color')

# Define visualization parameters
vis_params = {
    'min': 0,
    'max': 1,
    'palette': ['green', 'blue', 'red']
}

# Create a visualized image
visualized_true_color_image = true_color_image.visualize(**vis_params)

# Generate a download URL
url = visualized_true_color_image.getDownloadURL({
    'scale': 30,
    'crs': 'EPSG:4326',
    'region': aoi.toGeoJSONString(),
    'format': 'png'
})

print("Download URL:", url)