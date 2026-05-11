from pathlib import Path

import up42
import up42.http.oauth

credentials_file_path = Path(__file__).parent.parent / "secrets" / "up42_credentials.json"

if not credentials_file_path.is_file():
    raise FileNotFoundError(
        f"Credentials file not found at {credentials_file_path}. Please create the file with your UP42 credentials."
    )

try:
    up42.authenticate(cfg_file=credentials_file_path)
except up42.http.oauth.WrongCredentials as e:
    raise ValueError(
        f"Authentication failed. Please check your credentials in {credentials_file_path} and try again."
    ) from e

# from https://docs.up42.com/sdk/quick-start
archive_collections = up42.ProductGlossary.get_collections(
    collection_type=up42.CollectionType.ARCHIVE,
    sort_by=up42.CollectionSorting.name.asc,
)

for collection in archive_collections:
    print(f"\n{collection.title}: {collection.name}")
    print(f"{collection.description}")
    print("Metadata:")
    print(f"  Product type:       {collection.metadata.product_type}")
    print(f"  Resolution class:   {collection.metadata.resolution_class}")
    print(f"  Min resolution:     {collection.metadata.resolution_value.minimum} m")
    if collection.metadata.resolution_value.maximum:
        print(f"  Max resolution {collection.metadata.resolution_value.maximum} m")
