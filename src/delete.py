import os

def delete_local_file(file_path):
   
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File '{file_path}' has been deleted.")
        else:
            print(f"File '{file_path}' not found.")
    except Exception as e:
        print(f"Error deleting file: {e}")

if __name__ == "__main__":
    delete_local_file("resources/testFile.json")