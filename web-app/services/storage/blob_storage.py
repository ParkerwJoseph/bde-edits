import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, BinaryIO, Union
from pathlib import Path

from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    ContainerClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from config.settings import (
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_ACCOUNT_KEY,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class BlobStorageClient:
    """
    Azure Blob Storage client wrapper for file operations.
    Follows singleton pattern consistent with other services in the codebase.
    """

    _instance: Optional["BlobStorageClient"] = None

    def __init__(self):
        logger.info("=" * 60)
        logger.info("Initializing BlobStorageClient...")

        self.account_name = AZURE_STORAGE_ACCOUNT_NAME
        self.account_key = AZURE_STORAGE_ACCOUNT_KEY
        self.container_name = AZURE_STORAGE_CONTAINER_NAME
        self.connection_string = AZURE_STORAGE_CONNECTION_STRING

        self.blob_service_client: Optional[BlobServiceClient] = None
        self.container_client: Optional[ContainerClient] = None

        self._initialize_client()

        logger.info("=" * 60)

    def _initialize_client(self):
        """Initialize the Azure Blob Service Client."""
        try:
            # Prefer connection string if provided
            if self.connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                logger.info("BlobStorageClient initialized with connection string")
            elif self.account_name and self.account_key:
                # Build connection string from account name and key
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key
                )
                logger.info(f"BlobStorageClient initialized with account key")
                logger.info(f"  Account: {self.account_name}")
            else:
                logger.warning("BlobStorageClient NOT configured - missing credentials")
                return

            # Get container client
            if self.container_name:
                self.container_client = self.blob_service_client.get_container_client(
                    self.container_name
                )
                logger.info(f"  Container: {self.container_name}")

                # Ensure container exists
                self._ensure_container_exists()
            else:
                logger.warning("Container name not configured")

        except Exception as e:
            logger.error(f"Failed to initialize BlobStorageClient: {e}")
            self.blob_service_client = None
            self.container_client = None

    def _ensure_container_exists(self):
        """Create the container if it doesn't exist."""
        try:
            self.container_client.create_container()
            logger.info(f"  Container created: {self.container_name}")
        except ResourceExistsError:
            logger.info(f"  Container already exists: {self.container_name}")
        except Exception as e:
            logger.warning(f"  Could not verify container: {e}")

    @classmethod
    def get_instance(cls) -> "BlobStorageClient":
        """Get singleton instance of BlobStorageClient."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self.blob_service_client is not None and self.container_client is not None

    def _generate_blob_name(
        self,
        original_filename: str,
        tenant_id: str,
        company_id: str,
    ) -> str:
        """
        Generate a unique blob name with folder structure.

        Structure: {tenant_id}/{company_id}/{uuid}_{filename}

        Args:
            original_filename: Original file name
            tenant_id: Tenant ID for multi-tenant isolation (required)
            company_id: Company ID for company-level organization (required)

        Returns:
            Blob name in format: tenant_id/company_id/uuid_filename
        """
        # Extract extension
        extension = Path(original_filename).suffix.lower()
        base_name = Path(original_filename).stem

        # Generate unique name
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{unique_id}_{base_name}{extension}"

        # Build path: tenant_id/company_id/filename
        return f"{tenant_id}/{company_id}/{filename}"

    def upload_file(
        self,
        file_path: Union[str, Path],
        tenant_id: str,
        company_id: str,
        blob_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = True
    ) -> dict:
        """
        Upload a file from local filesystem to Azure Blob Storage.

        Args:
            file_path: Path to the local file
            tenant_id: Tenant ID for folder organization (required)
            company_id: Company ID for folder organization (required)
            blob_name: Optional custom blob name (auto-generated if not provided)
            content_type: Optional content type (auto-detected if not provided)
            metadata: Optional metadata to attach to the blob
            overwrite: Whether to overwrite existing blob

        Returns:
            Dict with blob_name, url, and signed_url
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate blob name if not provided
        if not blob_name:
            blob_name = self._generate_blob_name(
                file_path.name, tenant_id, company_id
            )

        logger.info(f"[Blob] Uploading file: {file_path.name} -> {blob_name}")

        # Get blob client
        blob_client = self.container_client.get_blob_client(blob_name)

        # Auto-detect content type
        if not content_type:
            content_type = self._get_content_type(file_path.suffix)

        # Upload file
        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data,
                overwrite=overwrite,
                content_settings=ContentSettings(content_type=content_type) if content_type else None,
                metadata=metadata
            )

        logger.info(f"[Blob] Upload complete: {blob_name}")

        return self._build_upload_response(blob_name, blob_client)

    def upload_file_from_bytes(
        self,
        data: bytes,
        filename: str,
        tenant_id: str,
        company_id: str,
        blob_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = True
    ) -> dict:
        """
        Upload file data (bytes) to Azure Blob Storage.

        Args:
            data: File content as bytes
            filename: Original filename (for extension detection)
            tenant_id: Tenant ID for folder organization (required)
            company_id: Company ID for folder organization (required)
            blob_name: Optional custom blob name
            content_type: Optional content type
            metadata: Optional metadata to attach to the blob
            overwrite: Whether to overwrite existing blob

        Returns:
            Dict with blob_name, url, and signed_url
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        # Generate blob name if not provided
        if not blob_name:
            blob_name = self._generate_blob_name(filename, tenant_id, company_id)

        logger.info(f"[Blob] Uploading bytes: {filename} ({len(data)} bytes) -> {blob_name}")

        # Get blob client
        blob_client = self.container_client.get_blob_client(blob_name)

        # Auto-detect content type
        if not content_type:
            extension = Path(filename).suffix
            content_type = self._get_content_type(extension)

        # Upload data
        blob_client.upload_blob(
            data,
            overwrite=overwrite,
            content_settings=ContentSettings(content_type=content_type) if content_type else None,
            metadata=metadata
        )

        logger.info(f"[Blob] Upload complete: {blob_name}")

        return self._build_upload_response(blob_name, blob_client)

    def upload_file_from_stream(
        self,
        stream: BinaryIO,
        filename: str,
        tenant_id: str,
        company_id: str,
        blob_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = True
    ) -> dict:
        """
        Upload file from a stream/file-like object to Azure Blob Storage.

        Args:
            stream: File-like object to upload
            filename: Original filename
            tenant_id: Tenant ID for folder organization (required)
            company_id: Company ID for folder organization (required)
            blob_name: Optional custom blob name
            content_type: Optional content type
            metadata: Optional metadata to attach to the blob
            overwrite: Whether to overwrite existing blob

        Returns:
            Dict with blob_name, url, and signed_url
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        # Generate blob name if not provided
        if not blob_name:
            blob_name = self._generate_blob_name(filename, tenant_id, company_id)

        logger.info(f"[Blob] Uploading stream: {filename} -> {blob_name}")

        # Get blob client
        blob_client = self.container_client.get_blob_client(blob_name)

        # Auto-detect content type
        if not content_type:
            extension = Path(filename).suffix
            content_type = self._get_content_type(extension)

        # Upload stream
        blob_client.upload_blob(
            stream,
            overwrite=overwrite,
            content_settings=ContentSettings(content_type=content_type) if content_type else None,
            metadata=metadata
        )

        logger.info(f"[Blob] Upload complete: {blob_name}")

        return self._build_upload_response(blob_name, blob_client)

    def _build_upload_response(self, blob_name: str, blob_client: BlobClient) -> dict:
        """Build the response dict for upload operations."""
        # Generate signed URL (default 24 hours)
        signed_url = self.get_signed_url(blob_name)

        return {
            "blob_name": blob_name,
            "url": blob_client.url,
            "signed_url": signed_url,
            "container": self.container_name,
            "account": self.account_name,
        }

    def download_file(
        self,
        blob_name: str,
        destination_path: Union[str, Path]
    ) -> Path:
        """
        Download a blob to local filesystem.

        Args:
            blob_name: Name of the blob to download
            destination_path: Local path to save the file

        Returns:
            Path to the downloaded file
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        destination_path = Path(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[Blob] Downloading: {blob_name} -> {destination_path}")

        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            with open(destination_path, "wb") as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())

            logger.info(f"[Blob] Download complete: {destination_path}")
            return destination_path

        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_name}")

    def download_file_to_bytes(self, blob_name: str) -> bytes:
        """
        Download a blob and return its content as bytes.

        Args:
            blob_name: Name of the blob to download

        Returns:
            Blob content as bytes
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        logger.info(f"[Blob] Downloading to bytes: {blob_name}")

        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            logger.info(f"[Blob] Downloaded {len(data)} bytes")
            return data

        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_name}")

    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a blob from storage.

        Args:
            blob_name: Name of the blob to delete

        Returns:
            True if deleted, False if not found
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        logger.info(f"[Blob] Deleting: {blob_name}")

        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            blob_client.delete_blob()
            logger.info(f"[Blob] Deleted: {blob_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"[Blob] Not found for deletion: {blob_name}")
            return False

    def get_signed_url(
        self,
        blob_name: str,
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        """
        Generate a Shared Access Signature (SAS) URL for a blob.

        Args:
            blob_name: Name of the blob
            expiry_hours: Hours until the URL expires (default 24)
            permissions: Permission string - 'r' for read, 'w' for write, 'd' for delete

        Returns:
            Signed URL string
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        # Parse permissions
        sas_permissions = BlobSasPermissions(
            read="r" in permissions,
            write="w" in permissions,
            delete="d" in permissions,
        )

        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=sas_permissions,
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )

        # Build full URL
        signed_url = (
            f"https://{self.account_name}.blob.core.windows.net/"
            f"{self.container_name}/{blob_name}?{sas_token}"
        )

        logger.info(f"[Blob] Generated signed URL for: {blob_name} (expires in {expiry_hours}h)")

        return signed_url

    def file_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in storage.

        Args:
            blob_name: Name of the blob to check

        Returns:
            True if exists, False otherwise
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.exists()

    def list_files(
        self,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> list:
        """
        List blobs in the container.

        Args:
            tenant_id: Optional tenant ID to filter by tenant folder
            company_id: Optional company ID to filter by company folder (requires tenant_id)

        Returns:
            List of blob names
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        # Build prefix: tenant_id/company_id/
        prefix = None
        if tenant_id and company_id:
            prefix = f"{tenant_id}/{company_id}/"
        elif tenant_id:
            prefix = f"{tenant_id}/"

        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]

    def get_blob_properties(self, blob_name: str) -> dict:
        """
        Get properties/metadata of a blob.

        Args:
            blob_name: Name of the blob

        Returns:
            Dict with blob properties
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            properties = blob_client.get_blob_properties()
            return {
                "name": blob_name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "created_on": properties.creation_time,
                "last_modified": properties.last_modified,
                "metadata": properties.metadata or {},
            }
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_name}")

    @staticmethod
    def _get_content_type(extension: str) -> Optional[str]:
        """Get content type from file extension."""
        content_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".xml": "application/xml",
            ".html": "text/html",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".zip": "application/zip",
        }
        return content_types.get(extension.lower())


# Singleton accessor
def get_blob_storage_client() -> BlobStorageClient:
    """Get the singleton BlobStorageClient instance."""
    return BlobStorageClient.get_instance()


# Convenience functions for direct use
def upload_file(
    file_path: Union[str, Path],
    tenant_id: str,
    company_id: str,
    **kwargs
) -> dict:
    """Upload a file from local filesystem."""
    return get_blob_storage_client().upload_file(
        file_path, tenant_id=tenant_id, company_id=company_id, **kwargs
    )


def upload_file_from_bytes(
    data: bytes,
    filename: str,
    tenant_id: str,
    company_id: str,
    **kwargs
) -> dict:
    """Upload file data (bytes) to storage."""
    return get_blob_storage_client().upload_file_from_bytes(
        data, filename, tenant_id=tenant_id, company_id=company_id, **kwargs
    )


def upload_file_from_stream(
    stream: BinaryIO,
    filename: str,
    tenant_id: str,
    company_id: str,
    **kwargs
) -> dict:
    """Upload file from a stream to storage."""
    return get_blob_storage_client().upload_file_from_stream(
        stream, filename, tenant_id=tenant_id, company_id=company_id, **kwargs
    )


def download_file(blob_name: str, destination_path: Union[str, Path]) -> Path:
    """Download a blob to local filesystem."""
    return get_blob_storage_client().download_file(blob_name, destination_path)


def download_file_to_bytes(blob_name: str) -> bytes:
    """Download a blob and return its content as bytes."""
    return get_blob_storage_client().download_file_to_bytes(blob_name)


def delete_file(blob_name: str) -> bool:
    """Delete a blob from storage."""
    return get_blob_storage_client().delete_file(blob_name)


def get_signed_url(blob_name: str, expiry_hours: int = 24) -> str:
    """Generate a signed URL for a blob."""
    return get_blob_storage_client().get_signed_url(blob_name, expiry_hours)


def file_exists(blob_name: str) -> bool:
    """Check if a blob exists."""
    return get_blob_storage_client().file_exists(blob_name)
