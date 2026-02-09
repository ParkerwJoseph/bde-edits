"""
Azure Queue Service for sending document and connector processing messages.
"""
import base64
import json
import time
from datetime import datetime
from typing import Optional, List

from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy
from azure.core.exceptions import ServiceRequestError, ServiceResponseError

from config.settings import (
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_ACCOUNT_KEY,
    DOCUMENT_PROCESSING_QUEUE,
    QUICKBOOK_PROCESSING_QUEUE,
    CARBONVOICE_PROCESSING_QUEUE,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Retry configuration
MAX_SEND_RETRIES = 3
RETRY_DELAY_SECONDS = 1


class QueueService:
    """Service for sending messages to Azure Storage Queue."""

    def __init__(self):
        self._document_queue_client: Optional[QueueClient] = None
        self._quickbooks_queue_client: Optional[QueueClient] = None
        self._carbonvoice_queue_client: Optional[QueueClient] = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize queue clients with Base64 encoding for Azure Functions compatibility."""
        if not AZURE_STORAGE_CONNECTION_STRING and not (AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY):
            logger.warning("[QueueService] No Azure Storage credentials configured")
            return

        # Initialize document queue client
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self._document_queue_client = QueueClient.from_connection_string(
                    conn_str=AZURE_STORAGE_CONNECTION_STRING,
                    queue_name=DOCUMENT_PROCESSING_QUEUE,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            else:
                account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
                self._document_queue_client = QueueClient(
                    account_url=account_url,
                    queue_name=DOCUMENT_PROCESSING_QUEUE,
                    credential=AZURE_STORAGE_ACCOUNT_KEY,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            logger.info(f"[QueueService] Initialized document queue: {DOCUMENT_PROCESSING_QUEUE}")
        except Exception as e:
            logger.error(f"[QueueService] Failed to initialize document queue: {e}")

        # Initialize QuickBooks queue client (separate try/except so document queue still works)
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self._quickbooks_queue_client = QueueClient.from_connection_string(
                    conn_str=AZURE_STORAGE_CONNECTION_STRING,
                    queue_name=QUICKBOOK_PROCESSING_QUEUE,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            else:
                account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
                self._quickbooks_queue_client = QueueClient(
                    account_url=account_url,
                    queue_name=QUICKBOOK_PROCESSING_QUEUE,
                    credential=AZURE_STORAGE_ACCOUNT_KEY,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            logger.info(f"[QueueService] Initialized QuickBooks queue: {QUICKBOOK_PROCESSING_QUEUE}")
        except Exception as e:
            logger.error(f"[QueueService] Failed to initialize QuickBooks queue: {e}")

        # Initialize Carbon Voice queue client
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self._carbonvoice_queue_client = QueueClient.from_connection_string(
                    conn_str=AZURE_STORAGE_CONNECTION_STRING,
                    queue_name=CARBONVOICE_PROCESSING_QUEUE,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            else:
                account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
                self._carbonvoice_queue_client = QueueClient(
                    account_url=account_url,
                    queue_name=CARBONVOICE_PROCESSING_QUEUE,
                    credential=AZURE_STORAGE_ACCOUNT_KEY,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            logger.info(f"[QueueService] Initialized Carbon Voice queue: {CARBONVOICE_PROCESSING_QUEUE}")
        except Exception as e:
            logger.error(f"[QueueService] Failed to initialize Carbon Voice queue: {e}")

    # Backward compatibility property
    @property
    def _queue_client(self) -> Optional[QueueClient]:
        return self._document_queue_client

    def is_configured(self) -> bool:
        """Check if the queue service is properly configured."""
        return self._document_queue_client is not None

    def is_quickbooks_configured(self) -> bool:
        """Check if the QuickBooks queue is properly configured."""
        return self._quickbooks_queue_client is not None

    def is_carbonvoice_configured(self) -> bool:
        """Check if the Carbon Voice queue is properly configured."""
        return self._carbonvoice_queue_client is not None
    def _reinitialize_document_queue(self) -> bool:
        """Reinitialize the document queue client. Returns True if successful."""
        logger.info("[QueueService] Reinitializing document queue client...")
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self._document_queue_client = QueueClient.from_connection_string(
                    conn_str=AZURE_STORAGE_CONNECTION_STRING,
                    queue_name=DOCUMENT_PROCESSING_QUEUE,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            else:
                account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
                self._document_queue_client = QueueClient(
                    account_url=account_url,
                    queue_name=DOCUMENT_PROCESSING_QUEUE,
                    credential=AZURE_STORAGE_ACCOUNT_KEY,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            logger.info("[QueueService] Document queue client reinitialized successfully")
            return True
        except Exception as e:
            logger.error(f"[QueueService] Failed to reinitialize document queue: {e}")
            return False

    def send_document_processing_message(
        self,
        document_id: str,
        blob_name: str,
        tenant_id: str,
        company_id: str,
        filename: str,
    ) -> bool:
        """
        Send a message to the document processing queue with retry logic.

        Args:
            document_id: The document ID in the database
            blob_name: The blob path in Azure Storage
            tenant_id: The tenant ID
            company_id: The company ID
            filename: The original filename

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self._document_queue_client:
            logger.error("[QueueService] Document queue client not initialized")
            # Try to reinitialize
            if not self._reinitialize_document_queue():
                return False

        message = {
            "document_id": document_id,
            "blob_name": blob_name,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "filename": filename,
            "queued_at": datetime.utcnow().isoformat(),
        }

        # Encode as bytes for BinaryBase64EncodePolicy
        message_json = json.dumps(message)
        message_bytes = message_json.encode('utf-8')

        last_error = None
        for attempt in range(1, MAX_SEND_RETRIES + 1):
            try:
                logger.info(f"[QueueService] Sending message for document {document_id} (attempt {attempt}/{MAX_SEND_RETRIES})")
                self._document_queue_client.send_message(message_bytes)
                logger.info(f"[QueueService] Message sent successfully for document: {document_id}")
                return True

            except (ServiceRequestError, ServiceResponseError) as e:
                # Network/connection errors - reinitialize and retry
                last_error = e
                logger.warning(f"[QueueService] Connection error on attempt {attempt}: {type(e).__name__}: {e}")
                if attempt < MAX_SEND_RETRIES:
                    logger.info(f"[QueueService] Reinitializing connection and retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    self._reinitialize_document_queue()

            except Exception as e:
                # Other errors - log and retry
                last_error = e
                logger.warning(f"[QueueService] Error on attempt {attempt}: {type(e).__name__}: {e}")
                import traceback
                logger.warning(f"[QueueService] Traceback: {traceback.format_exc()}")
                if attempt < MAX_SEND_RETRIES:
                    logger.info(f"[QueueService] Retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    # Also try reinitializing on general errors
                    self._reinitialize_document_queue()

        logger.error(f"[QueueService] Failed to send document message after {MAX_SEND_RETRIES} attempts: {last_error}")
        return False

    def _reinitialize_quickbooks_queue(self) -> bool:
        """Reinitialize the QuickBooks queue client. Returns True if successful."""
        logger.info("[QueueService] Reinitializing QuickBooks queue client...")
        try:
            if AZURE_STORAGE_CONNECTION_STRING:
                self._quickbooks_queue_client = QueueClient.from_connection_string(
                    conn_str=AZURE_STORAGE_CONNECTION_STRING,
                    queue_name=QUICKBOOK_PROCESSING_QUEUE,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            else:
                account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.queue.core.windows.net"
                self._quickbooks_queue_client = QueueClient(
                    account_url=account_url,
                    queue_name=QUICKBOOK_PROCESSING_QUEUE,
                    credential=AZURE_STORAGE_ACCOUNT_KEY,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                )
            logger.info("[QueueService] QuickBooks queue client reinitialized successfully")
            return True
        except Exception as e:
            logger.error(f"[QueueService] Failed to reinitialize QuickBooks queue: {e}")
            return False

    def send_quickbooks_processing_message(
        self,
        connector_config_id: str,
        tenant_id: str,
        company_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> bool:
        """
        Send a message to the QuickBooks processing queue with retry logic.

        Args:
            connector_config_id: The connector config ID in the database
            tenant_id: The tenant ID
            company_id: The company ID
            entity_types: Optional list of entity types to process

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self._quickbooks_queue_client:
            logger.error("[QueueService] QuickBooks queue client not initialized")
            if not self._reinitialize_quickbooks_queue():
                return False

        message = {
            "connector_config_id": connector_config_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "entity_types": entity_types,
            "queued_at": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }

        # Encode as bytes for BinaryBase64EncodePolicy
        message_json = json.dumps(message)
        message_bytes = message_json.encode('utf-8')

        last_error = None
        for attempt in range(1, MAX_SEND_RETRIES + 1):
            try:
                logger.info(f"[QueueService] Sending message for QuickBooks connector {connector_config_id} (attempt {attempt}/{MAX_SEND_RETRIES})")
                self._quickbooks_queue_client.send_message(message_bytes)
                logger.info(f"[QueueService] Message sent successfully for QuickBooks connector: {connector_config_id}")
                return True

            except (ServiceRequestError, ServiceResponseError) as e:
                last_error = e
                logger.warning(f"[QueueService] Connection error on attempt {attempt}: {type(e).__name__}: {e}")
                if attempt < MAX_SEND_RETRIES:
                    logger.info(f"[QueueService] Reinitializing connection and retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    self._reinitialize_quickbooks_queue()

            except Exception as e:
                last_error = e
                logger.warning(f"[QueueService] Error on attempt {attempt}: {type(e).__name__}: {e}")
                if attempt < MAX_SEND_RETRIES:
                    logger.info(f"[QueueService] Retrying in {RETRY_DELAY_SECONDS}s...")
                    time.sleep(RETRY_DELAY_SECONDS)
                    self._reinitialize_quickbooks_queue()

        logger.error(f"[QueueService] Failed to send QuickBooks message after {MAX_SEND_RETRIES} attempts: {last_error}")
        return False

    def send_carbonvoice_processing_message(
        self,
        connector_config_id: str,
        tenant_id: str,
        company_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> bool:
        """
        Send a message to the Carbon Voice processing queue.

        Args:
            connector_config_id: The connector config ID in the database
            tenant_id: The tenant ID
            company_id: The company ID
            entity_types: Optional list of entity types to process

        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self._carbonvoice_queue_client:
            logger.error("[QueueService] Carbon Voice queue client not initialized")
            return False

        try:
            message = {
                "connector_config_id": connector_config_id,
                "connector_type": "carbonvoice",
                "tenant_id": tenant_id,
                "company_id": company_id,
                "entity_types": entity_types,
                "queued_at": datetime.utcnow().isoformat(),
                "retry_count": 0,
            }

            # Encode as bytes for BinaryBase64EncodePolicy
            message_json = json.dumps(message)
            message_bytes = message_json.encode('utf-8')
            self._carbonvoice_queue_client.send_message(message_bytes)

            logger.info(f"[QueueService] Message sent for Carbon Voice connector: {connector_config_id}")
            return True

        except Exception as e:
            logger.error(f"[QueueService] Failed to send Carbon Voice message: {e}")
            return False


# Singleton instance
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Get the singleton queue service instance."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
