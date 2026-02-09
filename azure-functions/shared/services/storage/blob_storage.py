import uuid
import time
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
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, AzureError, ServiceRequestError
from azure.core.pipeline.policies import RetryPolicy

from shared.config.settings import (
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_ACCOUNT_KEY,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
)
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Azure SDK retry configuration for transient failures
RETRY_TOTAL = 5  # Total number of retries
RETRY_BACKOFF_FACTOR = 1.0  # Exponential backoff factor
RETRY_BACKOFF_MAX = 60  # Maximum backoff time in seconds


class BlobStorageClient:
    """Azure Blob Storage client wrapper."""

    _instance: Optional["BlobStorageClient"] = None

    def __init__(self):
        logger.info("Initializing BlobStorageClient...")

        self.account_name = AZURE_STORAGE_ACCOUNT_NAME
        self.account_key = AZURE_STORAGE_ACCOUNT_KEY
        self.container_name = AZURE_STORAGE_CONTAINER_NAME
        self.connection_string = AZURE_STORAGE_CONNECTION_STRING

        self.blob_service_client: Optional[BlobServiceClient] = None
        self.container_client: Optional[ContainerClient] = None

        self._initialize_client()

    def _initialize_client(self):
        try:
            # Connection settings with timeouts
            connection_timeout = 30  # seconds
            read_timeout = 120  # seconds

            # Retry policy for transient failures (connection drops, timeouts, etc.)
            retry_policy = {
                "retry_total": RETRY_TOTAL,
                "retry_backoff_factor": RETRY_BACKOFF_FACTOR,
                "retry_backoff_max": RETRY_BACKOFF_MAX,
                "retry_on_status_codes": [408, 429, 500, 502, 503, 504],
            }

            if self.connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string,
                    connection_timeout=connection_timeout,
                    read_timeout=read_timeout,
                    retry_total=RETRY_TOTAL,
                    retry_backoff_factor=RETRY_BACKOFF_FACTOR,
                    retry_backoff_max=RETRY_BACKOFF_MAX,
                )
                logger.info("BlobStorageClient initialized with connection string")
                logger.info(f"  Connection timeout: {connection_timeout}s, Read timeout: {read_timeout}s")
                logger.info(f"  Retry policy: {RETRY_TOTAL} retries, backoff factor: {RETRY_BACKOFF_FACTOR}")
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key,
                    connection_timeout=connection_timeout,
                    read_timeout=read_timeout,
                    retry_total=RETRY_TOTAL,
                    retry_backoff_factor=RETRY_BACKOFF_FACTOR,
                    retry_backoff_max=RETRY_BACKOFF_MAX,
                )
                logger.info(f"BlobStorageClient initialized with account key")
                logger.info(f"  Connection timeout: {connection_timeout}s, Read timeout: {read_timeout}s")
                logger.info(f"  Retry policy: {RETRY_TOTAL} retries, backoff factor: {RETRY_BACKOFF_FACTOR}")
            else:
                logger.warning("BlobStorageClient NOT configured")
                return

            if self.container_name:
                self.container_client = self.blob_service_client.get_container_client(
                    self.container_name
                )
                logger.info(f"  Container: {self.container_name}")
            else:
                logger.warning("Container name not configured")

            # Track initialization time to detect stale connections
            self._initialized_at = time.time()

        except Exception as e:
            logger.error(f"Failed to initialize BlobStorageClient: {e}")
            self.blob_service_client = None
            self.container_client = None

    @classmethod
    def get_instance(cls) -> "BlobStorageClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_configured(self) -> bool:
        return self.blob_service_client is not None and self.container_client is not None

    def check_connection_health(self, timeout_seconds: int = 10) -> bool:
        """
        Verify the blob storage connection is healthy before starting operations.

        Args:
            timeout_seconds: Maximum time to wait for health check

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_configured():
            logger.warning("[Blob] Health check failed: Client not configured")
            return False

        try:
            start_time = time.time()
            # Try to get container properties as a lightweight health check
            # This validates both network connectivity and authentication
            self.container_client.get_container_properties(timeout=timeout_seconds)
            check_time = time.time() - start_time
            logger.info(f"[Blob] Connection health check passed in {check_time:.2f}s")
            return True
        except Exception as e:
            logger.error(f"[Blob] Connection health check failed: {type(e).__name__}: {e}")
            return False

    def ensure_connection_healthy(self, timeout_seconds: int = 10) -> None:
        """
        Ensure blob storage connection is healthy, reinitialize if needed.

        Args:
            timeout_seconds: Maximum time to wait for health check

        Raises:
            ConnectionError: If connection cannot be established after reinitialization
        """
        if self.check_connection_health(timeout_seconds):
            return

        logger.warning("[Blob] Connection unhealthy, attempting to reinitialize...")
        self._initialize_client()

        if not self.check_connection_health(timeout_seconds):
            raise ConnectionError("Failed to establish healthy connection to blob storage after reinitialization")

    def download_file(
        self,
        blob_name: str,
        destination_path: Union[str, Path],
        timeout_seconds: int = 120,
        validate_connection: bool = True
    ) -> Path:
        """
        Download a blob to a local file with timeout and detailed logging.

        Args:
            blob_name: Name of the blob to download
            destination_path: Local path to save the file
            timeout_seconds: Maximum time to wait for download (default 120s)
            validate_connection: Whether to validate connection health before download (default True)
        """
        if not self.is_configured():
            logger.error("[Blob] BlobStorageClient is not configured!")
            raise ValueError("BlobStorageClient is not configured")

        # Validate connection health before starting download
        if validate_connection:
            try:
                self.ensure_connection_healthy(timeout_seconds=10)
            except ConnectionError as e:
                logger.error(f"[Blob] Connection validation failed: {e}")
                raise

        destination_path = Path(destination_path)

        logger.info(f"[Blob] === Starting Download ===")
        logger.info(f"[Blob]   Blob: {blob_name}")
        logger.info(f"[Blob]   Destination: {destination_path}")
        logger.info(f"[Blob]   Timeout: {timeout_seconds}s")

        # Create parent directory
        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[Blob]   Directory ready: {destination_path.parent}")
        except Exception as e:
            logger.error(f"[Blob]   Failed to create directory: {e}")
            raise

        # Get blob client
        start_time = time.time()
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            logger.info(f"[Blob]   Got blob client in {time.time() - start_time:.2f}s")
        except Exception as e:
            logger.error(f"[Blob]   Failed to get blob client: {e}")
            raise

        # Skip existence check - just try to download directly
        # The download will fail with ResourceNotFoundError if blob doesn't exist
        # This avoids the HEAD request that can hang

        # Download the blob directly
        try:
            logger.info(f"[Blob]   Starting download (skipping existence check)...")
            download_start = time.time()

            # Use timeout parameter for the download operation
            download_stream = blob_client.download_blob(
                max_concurrency=1,  # Reduce concurrency to avoid connection issues
                timeout=timeout_seconds
            )

            logger.info(f"[Blob]   Download stream created in {time.time() - download_start:.2f}s")
            logger.info(f"[Blob]   Reading data...")

            read_start = time.time()
            data = download_stream.readall()
            read_time = time.time() - read_start

            logger.info(f"[Blob]   Read {len(data)} bytes in {read_time:.2f}s")

            # Write to file
            write_start = time.time()
            with open(destination_path, "wb") as file:
                file.write(data)
            write_time = time.time() - write_start

            total_time = time.time() - start_time
            logger.info(f"[Blob]   Written to file in {write_time:.2f}s")
            logger.info(f"[Blob] === Download Complete ===")
            logger.info(f"[Blob]   Total time: {total_time:.2f}s")
            logger.info(f"[Blob]   File size on disk: {destination_path.stat().st_size} bytes")

            return destination_path

        except ResourceNotFoundError:
            logger.error(f"[Blob]   Blob not found during download: {blob_name}")
            raise FileNotFoundError(f"Blob not found: {blob_name}")
        except ServiceRequestError as e:
            # This is the specific error for connection failures (network issues, stale connections)
            logger.error(f"[Blob]   Connection/network error during download: {type(e).__name__}: {e}")
            logger.error(f"[Blob]   This is typically a transient error - retry should help")
            raise ConnectionError(f"Blob storage connection failed: {e}")
        except AzureError as e:
            logger.error(f"[Blob]   Azure error during download: {type(e).__name__}: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"[Blob]   Download timed out after {timeout_seconds}s: {e}")
            raise
        except Exception as e:
            logger.error(f"[Blob]   Unexpected error during download: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[Blob]   Traceback: {traceback.format_exc()}")
            raise

    def download_file_to_bytes(self, blob_name: str, timeout_seconds: int = 120) -> bytes:
        """
        Download a blob directly to bytes with timeout protection.

        Args:
            blob_name: Name of the blob to download
            timeout_seconds: Maximum time to wait for download (default 120s)
        """
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        logger.info(f"[Blob] Downloading to bytes: {blob_name} (timeout: {timeout_seconds}s)")

        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            download_start = time.time()
            download_stream = blob_client.download_blob(
                max_concurrency=1,  # Reduce concurrency to avoid connection issues
                timeout=timeout_seconds
            )
            data = download_stream.readall()
            download_time = time.time() - download_start
            logger.info(f"[Blob] Downloaded {len(data)} bytes in {download_time:.2f}s")
            return data

        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_name}")
        except AzureError as e:
            logger.error(f"[Blob] Azure error during download: {type(e).__name__}: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"[Blob] Download timed out after {timeout_seconds}s: {e}")
            raise

    def get_signed_url(
        self,
        blob_name: str,
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        sas_permissions = BlobSasPermissions(
            read="r" in permissions,
            write="w" in permissions,
            delete="d" in permissions,
        )

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=sas_permissions,
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )

        signed_url = (
            f"https://{self.account_name}.blob.core.windows.net/"
            f"{self.container_name}/{blob_name}?{sas_token}"
        )

        return signed_url

    def file_exists(self, blob_name: str) -> bool:
        if not self.is_configured():
            raise ValueError("BlobStorageClient is not configured")

        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.exists()


def get_blob_storage_client(force_new: bool = False) -> BlobStorageClient:
    """
    Get the BlobStorageClient instance.

    Args:
        force_new: If True, create a new instance instead of using cached one.
                   RECOMMENDED: Use force_new=True for download operations to avoid
                   stale connection issues in serverless environments.
    """
    if force_new:
        logger.info("[Blob] Creating fresh BlobStorageClient (force_new=True)")
        BlobStorageClient._instance = None
        return BlobStorageClient.get_instance()

    # Check if existing instance is stale (older than 5 minutes)
    # Stale connections are a common cause of intermittent failures in Azure Functions
    instance = BlobStorageClient._instance
    if instance is not None:
        age = time.time() - getattr(instance, '_initialized_at', 0)
        if age > 300:  # 5 minutes
            logger.info(f"[Blob] Existing client is stale ({age:.0f}s old), creating fresh instance")
            BlobStorageClient._instance = None

    return BlobStorageClient.get_instance()
