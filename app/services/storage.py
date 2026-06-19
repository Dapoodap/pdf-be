import datetime
from google.cloud import storage
from google.oauth2 import service_account
from app.core.config import settings

def get_gcs_client():
    private_key = settings.GCS_PRIVATE_KEY.replace("\\n", "\n")
    
    # Ensure the key starts and ends with quotes removed if they exist in the env var
    if private_key.startswith('"') and private_key.endswith('"'):
        private_key = private_key[1:-1]
        
    credentials_dict = {
        "type": "service_account",
        "project_id": settings.GCS_PROJECT_ID,
        "private_key": private_key,
        "client_email": settings.GCS_CLIENT_EMAIL,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{settings.GCS_CLIENT_EMAIL.replace('@', '%40')}"
    }

    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = storage.Client(credentials=credentials, project=settings.GCS_PROJECT_ID)
    return client

import mimetypes

def upload_file_to_gcs(file_bytes: bytes, service_name: str, filename: str) -> str:
    """
    Uploads a file to GCS and returns the path within the bucket.
    """
    client = get_gcs_client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    
    destination_blob_name = f"pdf/{service_name}/{filename}"
    
    blob = bucket.blob(destination_blob_name)
    
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"
        
    blob.upload_from_string(file_bytes, content_type=content_type)
    
    return destination_blob_name

def generate_presigned_url(blob_name: str, expiration_minutes: int = 60) -> str:
    """
    Generates a presigned URL to download a specific file.
    """
    client = get_gcs_client()
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    
    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="GET",
    )
    return url
