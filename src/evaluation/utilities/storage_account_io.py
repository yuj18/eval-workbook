from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def read_blob_from_uri(blob_uri):
    """
    Read a file from Azure blob storage using full URI

    Args:
        blob_uri: Full blob URI
        (e.g., https://account.blob.core.windows.net/container/path/file.json)

    Returns:
        File content as string
    """
    try:
        # Parse the URI to extract components
        if not blob_uri.startswith("https://"):
            raise ValueError("URI must start with https://")

        # Remove protocol and split
        uri_parts = blob_uri.replace("https://", "").split("/")
        storage_account_name = uri_parts[0].split(".")[0]
        container_name = uri_parts[1]
        blob_path = "/".join(uri_parts[2:])

        print(f"Storage Account: {storage_account_name}")
        print(f"Container: {container_name}")
        print(f"Blob Path: {blob_path}")

        # Create blob service client with credential
        blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=DefaultAzureCredential(),
        )

        # Get blob client
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_path
        )

        # Download content
        content = blob_client.download_blob().readall().decode("utf-8")
        print(f"Successfully read {len(content)} characters")

        return content

    except Exception as e:
        print(f"Error reading blob from URI: {e}")
        return None
