# pip install google-cloud-storage

import os
from google.cloud import storage

def upload_delete(bucket_name, source_folder, credential):
    try:
        client = storage.Client.from_service_account_json(credential)
        bucket = client.bucket(bucket_name)

        for root, dirs, files in os.walk(source_folder):
            for file in files:
                source_file_path = os.path.join(root, file)  
                destination_blob = os.path.relpath(source_file_path, source_folder).replace("\\", "/")
                total_size = os.path.getsize(source_file_path)
                blob = bucket.blob(destination_blob)
                blob.upload_from_filename(source_file_path)
                if not file.endswith(".json"):
                    os.remove(source_file_path)

    except Exception as e:
        print(f"Error: {e}")


#if __name__ == "__main__":
    # Change 'resources' to the folder containing your files
 #   upload("marinelitter_predicted", "resources", 'D:/Arbeit/credentials.json')