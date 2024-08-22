# install essential packages
# - pip install earthengine-api: for connection with GEE
# - pip install earthengine-api --upgrade (optional)
# - pip install marinedebrisdetector : model installation


# import essential packages, classes
import ee
import json 
import time
import requests


# authenticate with GCP account
ee.Authenticate()
# ee.Authenticate(force=True)

# initialize Earth Engine
try:
    ee.Initialize(project = "test-project-422119") #cloud_project_id
    print("Earth Engine is initialized.")
except ee.EEException as e:
    print("The Earth Engine API failed to initialize:", e)
   
# Reading coordinates from JSON
with open('src/coordinates.json', 'r') as file:
    data = json.load(file) 
    
coordinates = data['features'][0]['geometry']['coordinates']

# retrive image collection from aoi and given time intervall
def get_image_collection(coordinates, date_from, date_to):
    
    aoi = ee.Geometry.MultiPolygon(coordinates)
   # aoi = ee.Geometry.Polygon(coordinates)
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(aoi).filterDate(ee.Date(date_from), ee.Date(date_to))
    return collection, aoi

# export single image to oneDrive
def export_image_toDrive(image, aoi, folder):
    image_id = image.id().getInfo()
    description = "Original_" + image_id

    # cast all bands datatypes to Uint32
    image_uint32 = image.toUint32() 

    # dowload to oneDrive
    task = ee.batch.Export.image.toDrive(
        image = image_uint32,
        description = description ,
        folder = folder,
        region = aoi,
        scale = 10, # 10 meter/Pixel
        fileFormat='GeoTIFF'
    )

    task.start()
        # Wait for the task to complete
    print('Exporting image to Google Drive. This may take some time...')

    if task.status()['state'] in ['FAILED']:
        print("error")

    while task.status()['state'] in ['READY', 'RUNNING']:
        time.sleep(30)  # wait for 30 seconds before checking the status again
        print('Status:', task.status())

    print('Export completed.')

# export single image to gcp cloudStorage
def export_image_toStorage(image, aoi, bucket):
    image_id = image.id().getInfo()
    description = "Original_" + image_id

    # cast all bands datatypes to Uint32
    image_uint32 = image.toUint32() 
    task = ee.batch.Export.image.toCloudStorage(
        image = image_uint32,
        description = description,
        bucket = bucket,
        fileNamePrefix = 'prefix',
        region = aoi,
        scale = 10, # 10 meter
        fileFormat='GeoTIFF'
    )

    task.start()
        # Wait for the task to complete
    print('Exporting image to Google CloudStorage. This may take some time...')

    if task.status()['state'] in ['FAILED']:
        print("error")

    while task.status()['state'] in ['READY', 'RUNNING']:
        time.sleep(30)  # wait for 30 seconds before checking the status again
        print('Status:', task.status())

    print('Export completed.')

# export all images from collection
def export_imageCollection(collection, aoi, storage_type, save_location):
    image_ids = collection.aggregate_array("system:id").getInfo()
    for image_id in image_ids:
        image = ee.image(image_id)
        if storage_type.lower() == "drive":
           export_image_toDrive(image, aoi, save_location)
        else: 
            export_image_toStorage(image, aoi, save_location)


# test method
collection, aoi = get_image_collection(coordinates, '2019-07-15', '2019-07-16')
count = collection.size().getInfo()
print(f"There are {count} images in the collection")
# export_image_toDrive(collection.first(), aoi, 'Original_Images')
# export_imageCollection(collection, aoi, "Drive", 'Original_Images')



