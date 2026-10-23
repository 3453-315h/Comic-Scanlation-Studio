"""
Cloud Storage Module - Comic Translation Studio

Manages Google Cloud Storage for images with configurable access control.
"""

import logging
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)


class CloudStorageManager:
    """Manages Google Cloud Storage for images"""

    def __init__(self, bucket_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        logger.info(f"Initialized CloudStorageManager for bucket: {bucket_name}")

    def upload_image(self, local_path: Path, cloud_path: str) -> str | None:
        """Upload an image to cloud storage

        Args:
            local_path: Path to local file
            cloud_path: Destination path in cloud storage

        Returns:
            gs:// URI on success, or None on failure
        """
        try:
            blob = self.bucket.blob(cloud_path)
            blob.upload_from_filename(str(local_path))

            logger.info(f"Uploaded {local_path} to {cloud_path} (private)")
            return f"gs://{self.bucket.name}/{cloud_path}"
        except Exception as e:
            logger.error(f"Upload failed for {local_path}: {e}")
            return None

    def download_image(self, cloud_path: str, local_path: Path) -> bool:
        """Download an image from cloud storage"""
        try:
            blob = self.bucket.blob(cloud_path)
            blob.download_to_filename(str(local_path))
            logger.info(f"Downloaded {cloud_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Download failed for {cloud_path}: {e}")
            return False

    def delete_image(self, cloud_path: str) -> bool:
        """Delete an image from cloud storage"""
        try:
            blob = self.bucket.blob(cloud_path)
            blob.delete()
            logger.info(f"Deleted {cloud_path}")
            return True
        except Exception as e:
            logger.error(f"Delete failed for {cloud_path}: {e}")
            return False

    def get_signed_url(self, cloud_path: str, expiration_minutes: int = 60) -> str | None:
        """Generate a signed URL for temporary access (more secure than public)

        Args:
            cloud_path: Path to the file in cloud storage
            expiration_minutes: Minutes until the URL expires

        Returns:
            Signed URL, or None on failure
        """
        try:
            from datetime import timedelta
            blob = self.bucket.blob(cloud_path)
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            logger.info(f"Generated signed URL for {cloud_path} (expires in {expiration_minutes}m)")
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {cloud_path}: {e}")
            return None
