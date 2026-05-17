"""Google Cloud Storage client for contract file management."""
import uuid
from typing import Optional

from config import GCS_BUCKET_NAME, GOOGLE_CLOUD_PROJECT


def upload_to_gcs(file_bytes: bytes, filename: str, mime_type: str) -> Optional[str]:
    """Upload file to GCS and return the blob name.

    Args:
        file_bytes: Raw bytes of the file to upload.
        filename: Original filename.
        mime_type: MIME type of the file.

    Returns:
        GCS blob name if successful, None on failure.
    """
    try:
        from google.cloud import storage

        client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob_name = f"contracts/{uuid.uuid4()}/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(file_bytes, content_type=mime_type)
        return blob_name
    except Exception:
        return None


def get_signed_url(blob_name: str, expiration_seconds: int = 3600) -> Optional[str]:
    """Generate a signed URL for a GCS blob.

    Args:
        blob_name: The GCS blob path.
        expiration_seconds: URL expiry duration in seconds.

    Returns:
        Signed URL string if successful, None on failure.
    """
    try:
        import datetime
        from google.cloud import storage

        client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(blob_name)
        url = blob.generate_signed_url(
            expiration=datetime.timedelta(seconds=expiration_seconds),
            method="GET",
        )
        return url
    except Exception:
        return None
