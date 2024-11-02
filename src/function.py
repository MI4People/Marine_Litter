# install essential packages
# - pip install earthengine-api: for connection with GEE
# - pip install earthengine-api --upgrade (optional)
# - pip install marinedebrisdetector : model installation
# - pip install rasterio
# - pip install earthengine-api google-cloud-storage


# import essential packages, classes
import ee
import json 
import time
import csv
from io import StringIO 
import os
# from datetime import datetime
# import rasterio
from google.cloud import storage

class EarthEngineExporter:
    def __init__(self, project_id, bucket_name=None):
        self.project_id = project_id
        self.bucket_name = bucket_name
        ee.Authenticate()
        try:
            ee.Initialize(project=self.project_id)
            print("Earth Engine is initialized.")
        except ee.EEException as e:
            print("The Earth Engine API failed to initialize:", e)
            raise

    def read_coordinates_from_json(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data['features'][0]['geometry']['coordinates']

    def get_image_collection(self, coordinates, date_from, date_to):
        aoi = ee.Geometry.MultiPolygon(coordinates)
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                     .filterBounds(aoi) \
                     .filterDate(ee.Date(date_from), ee.Date(date_to))
        return collection, aoi

    def export_image(self, image, aoi, storage_type, storage_location):
        
        image_id = image.id().getInfo()
        image_uint32 = image.toUint32() # cast bands with same datatype
        
        # export functions
        export_func = (ee.batch.Export.image.toDrive if storage_type == 'drive' 
                   else ee.batch.Export.image.toCloudStorage)
        kwargs = {
        'image': image_uint32,
        'description': f"Original_{image_id}",
        'region': aoi,
        'scale': 10,
        'fileFormat': 'GeoTIFF'
        }

        if storage_type == 'drive':
            kwargs.update({'folder': storage_location})
        else:
            kwargs.update({'bucket': storage_location, 'fileNamePrefix': image_id})
            
        task = export_func(**kwargs)
        task.start()
        self._wait_for_task_completion(task)

    def _wait_for_task_completion(self, task):
        print('Exporting image. This may take some time...')
        while task.status()['state'] in ['READY', 'RUNNING']:
            time.sleep(30)
            print('Status:', task.status())

        if task.status()['state'] == 'FAILED':
            print("Export failed.")
        else:
            print('Export completed.')

    def extract_info(self, image):
        geom = image.geometry().bounds().coordinates().getInfo()[0]
        date = image.date().format('YYYY-MM-dd').getInfo()
        image_id = image.id().getInfo()
        coords = [f"({coord[0]}, {coord[1]})" for coord in geom]
        return [image_id, date] + coords

    def save_metadata_to_csv(self, filename, metadata):
        client = storage.Client()
        bucket = client.get_bucket(self.bucket_name)
        blob = bucket.blob(filename)
        existing_data = blob.download_as_text() if blob.exists() else ''
        
        with open('/tmp/' + filename, 'w', newline='') as tmp:
            writer = csv.writer(tmp)
            if not existing_data:
                writer.writerow(['ImageID', 'Date', 'Coordinate'])
            tmp.write(existing_data)
            writer.writerows(metadata)

        blob.upload_from_filename('/tmp/' + filename, content_type='text/csv')
        os.remove('/tmp/' + filename)

    def export_image_collection(self, collection, aoi, storage_type, save_location):
        image_info = collection.map(self.extract_info).getInfo()
        flattened_data = [[info[0], info[1], coord] for info in image_info for coord in info[2:]]
        self.save_metadata_to_csv("history.csv", flattened_data)
        
        image_ids = collection.aggregate_array("system:id").getInfo()
        for image_id in image_ids:
            image = ee.Image(image_id)
            if storage_type.lower() == "drive":
                self.export_image_to_drive(image, aoi, save_location)
            elif storage_type.lower() == "storage":
                if not self.bucket_name:
                    raise ValueError("bucket_name must be specified for Google Cloud Storage.")
                self.export_image_to_storage(image, aoi)
            else:
                raise ValueError("Invalid storage_type. Choose either 'drive' or 'storage'.")

def main():
    project_id = "test-project-422119"  # Replace with your GCP project ID
    bucket_name = "bucket-name"  # Replace with your GCS bucket name
    exporter = EarthEngineExporter(project_id, bucket_name)

    coordinates = exporter.read_coordinates_from_json('src/coordinates.json')
    collection, aoi = exporter.get_image_collection(coordinates, '2019-07-15', '2019-07-16')
    count = collection.size().getInfo()
    print(f"There are {count} images in the collection")

    # exporter.export_image_collection(collection, aoi, storage_type='drive', save_location='folder')
    # or
    # exporter.export_image_collection(collection, aoi, storage_type='storage', save_location='path/to/save_location')

if __name__ == "__main__":
    main()
