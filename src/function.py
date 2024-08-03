# install essential packages
# - pip install earthengine-api: for connection with GEE
# import essential packages, classes
import ee
import json 

# authenticate with GEE account
# TODO if the authentication is successful, then skip
ee.Authenticate()
# Initialize Earth Engine
ee.Initialize()
print("Earth Engine is initialized.")

# Reading JSON from a file
# TODO define coordinates
# with open('coordinates.json', 'r') as file:
#     data = json.load(file) 

# coordinates = data['features'][0]['geometry']['coordinates']

# example to test
coordinates = [
    [
        [
            [-122.292, 37.901],
            [-122.292, 37.90],
            [-122.29, 37.90],
            [-122.29, 37.901],
            [-122.292, 37.901]
        ]
    ]
]
aoi = ee.Geometry.MultiPolygon(coordinates)

# Filter Sentinel-2 Surface Reflectance image collection for given date range and area.
# collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
#               .filterDate('2019-07-15', '2019-07-20')
#               .filterBounds(aoi)
#               .first())
# true_color_image = collection.normalizedDifference(['B4', 'B3', 'B2']).rename('True color')

# helf function to count image collection
def count_images_in_collection(collection):

    def count_images_from_start(start, num):

        # Get a subset of the collection
        subset = collection.toList(num, start)
        return subset.size().getInfo()

    total_images = 0
    batch_size = 100  # Number of images to process per batch

    # Try to count images in batches until no more images are found
    start_index = 0
    while True:
        count = count_images_from_start(start_index, batch_size)
        if count == 0:
            break
        total_images += count
        start_index += batch_size

    return total_images

# helf function to count image size
def estimate_image_size(image):
    
    # Retrieve image properties
    image_info = image.getInfo()
    
    # Get dimensions and number of bands
    width = image_info['bands'][0]['dimensions'][0]
    height = image_info['bands'][0]['dimensions'][1]
    num_bands = len(image_info['bands'])
    
    # Sentinel-2 images are 16-bit per pixel
    bit_depth = 16
    bytes_per_pixel = bit_depth / 8
    
    # Calculate size of one image in bytes
    total_pixels = width * height
    image_size_bytes = total_pixels * num_bands * bytes_per_pixel
    
    # Convert bytes to megabytes
    image_size_mb = image_size_bytes / (1024 * 1024)
    
    return image_size_mb

# get the imge collection size
def filter_sentinel2_image(coordinates, date_from, date_to):
    aoi = ee.Geometry.MultiPolygon(coordinates)
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate(ee.Date(date_from), ee.Date(date_to))
    
    # Example usage
    total_images = count_images_in_collection(collection)
    print('Number of images:', total_images)
    
    first_image = collection.first()

    # # Define visualization parameters
    # TODO which band do we need for modeling -> image processing
    # vis_params = {
    #     'min': 0,
    #     'max': 1,
    #     'palette': ['green', 'blue', 'red']
    # }

    # # Create a visualized image
    # visualized_true_color_image = first_image.visualize(**vis_params)

    # # Generate a download URL
    # url = visualized_true_color_image.getDownloadURL({
    #     'scale': 30,
    #     'crs': 'EPSG:4326',
    #     'region': aoi.toGeoJSONString(),
    #     'format': 'png'
    # })

    # print("Download URL:", url)

    size_mb = estimate_image_size(first_image)
    print(f'Estimated size of one image: {size_mb:.2f} MB')

    size_collection = total_images * size_mb
    print('Size of image Collection:', size_collection)

    # throws errors because of limited memory
    # num_images = collection.size().getInfo()
    # print('Number of images:', num_images)
    # return num_images   

# test method
filter_sentinel2_image(coordinates, '2019-07-15', '2019-07-20')

# TODO image processing


