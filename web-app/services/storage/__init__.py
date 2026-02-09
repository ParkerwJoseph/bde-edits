from .blob_storage import (
    BlobStorageClient,
    get_blob_storage_client,
    upload_file,
    upload_file_from_bytes,
    upload_file_from_stream,
    download_file,
    download_file_to_bytes,
    delete_file,
    get_signed_url,
    file_exists,
)
from .queue_service import QueueService, get_queue_service


def send_quickbooks_processing_message(
    connector_config_id: str,
    tenant_id: str,
    company_id: str,
    entity_types: list = None,
) -> bool:
    """Helper function to send QuickBooks processing message to queue."""
    queue_service = get_queue_service()
    return queue_service.send_quickbooks_processing_message(
        connector_config_id=connector_config_id,
        tenant_id=tenant_id,
        company_id=company_id,
        entity_types=entity_types,
    )


def send_carbonvoice_processing_message(
    connector_config_id: str,
    tenant_id: str,
    company_id: str,
    entity_types: list = None,
) -> bool:
    """Helper function to send Carbon Voice processing message to queue."""
    queue_service = get_queue_service()
    return queue_service.send_carbonvoice_processing_message(
        connector_config_id=connector_config_id,
        tenant_id=tenant_id,
        company_id=company_id,
        entity_types=entity_types,
    )


__all__ = [
    "BlobStorageClient",
    "get_blob_storage_client",
    "upload_file",
    "upload_file_from_bytes",
    "upload_file_from_stream",
    "download_file",
    "download_file_to_bytes",
    "delete_file",
    "get_signed_url",
    "file_exists",
    "QueueService",
    "get_queue_service",
    "send_quickbooks_processing_message",
    "send_carbonvoice_processing_message",
]
