# pip install google-cloud-storage
# load secret from .secret
# pip install python-dotenv

import os
from dotenv import load_dotenv
from google.cloud import storage

# Load the .secret file
load_dotenv('.secret')
gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)  

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_path)
        print(f"File {source_file_path} uploaded to {destination_blob_name} in bucket {bucket_name}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upload_to_gcs("marinelitter_predicted", "resources/testFile.json", "testFile.json")
