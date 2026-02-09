import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session, select, func

from database.connection import get_session
from database.models import User, Company
from database.models.document import (
    Document, DocumentStatus, DocumentType,
    DocumentChunk, BDEPillar, ChunkType
)
from az_auth.dependencies import get_current_user, require_permission
from core.permissions import Permissions
from services.document_processor import DocumentProcessor
from services.storage import get_blob_storage_client, get_queue_service
from services.chunking import get_chunking_service, ChunkInput, SourceType
from config.settings import MAX_FILE_SIZE, UPLOAD_DIR, WEBHOOK_SECRET
from api.document.schemas import (
    DocumentResponse, DocumentListResponse,
    ChunkResponse, DocumentWithChunksResponse,
    ProcessingStatusResponse, UploadResponse
)
from utils.logger import get_logger
from api.document.websocket_manager import ws_manager

logger = get_logger(__name__)

router = APIRouter()


# Processing steps definition
PROCESSING_STEPS = {
    1: {"name": "Uploading", "progress": 0},
    2: {"name": "Analyzing Document", "progress": 20},
    3: {"name": "Creating Chunks", "progress": 50},
    4: {"name": "Generating Embeddings", "progress": 75},
    5: {"name": "Storing Results", "progress": 90},
    6: {"name": "Completed", "progress": 100},
}


# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".xlsx"}

# Allowed audio extensions
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}


def get_file_type(filename: str) -> DocumentType:
    """Get document type from filename extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return DocumentType.PDF
    elif ext == ".pptx":
        return DocumentType.PPTX
    elif ext == ".docx":
        return DocumentType.DOCX
    elif ext == ".xlsx":
        return DocumentType.XLSX
    elif ext in ALLOWED_AUDIO_EXTENSIONS:
        return DocumentType.AUDIO
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# Webhook payload schema
class WebhookPayload(BaseModel):
    """Payload received from Azure Function webhook."""
    document_id: str
    status: str  # "processing", "completed", or "failed"
    step: Optional[int] = None  # Current processing step (1-6)
    step_name: Optional[str] = None  # Human-readable step name
    progress: Optional[int] = None  # Progress percentage (0-100)
    total_pages: Optional[int] = None
    processed_pages: Optional[int] = None
    chunks_count: Optional[int] = None
    usage_stats: Optional[dict] = None
    error_message: Optional[str] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """
    Upload a document for processing.
    Supports PDF, DOCX, XLSX, PPTX, and audio files.
    Processing is triggered automatically via Azure Blob Storage trigger.
    """
    logger.info(f"[Upload] Received file: {file.filename}")
    logger.info(f"[Upload] Company ID: {company_id}")

    # Validate company exists and belongs to user's tenant
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    all_allowed = ALLOWED_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS
    if ext not in all_allowed:
        logger.warning(f"[Upload] Rejected - invalid extension: {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(sorted(all_allowed))}"
        )

    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    logger.info(f"[Upload] File size: {file_size_mb:.2f} MB")

    # Validate file size only if MAX_FILE_SIZE is set (non-zero)
    if MAX_FILE_SIZE > 0 and len(content) > MAX_FILE_SIZE:
        logger.warning(f"[Upload] Rejected - file too large: {len(content)} bytes")
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f} MB"
        )

    # Get file type
    try:
        file_type = get_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Upload to Azure Blob Storage
    blob_storage = get_blob_storage_client()
    blob_name = None
    blob_url = None
    signed_url = None
    signed_url_expiry = None

    if blob_storage.is_configured():
        logger.info(f"[Upload] Uploading to Azure Blob Storage...")
        try:
            blob_result = blob_storage.upload_file_from_bytes(
                data=content,
                filename=file.filename,
                tenant_id=user.tenant_id,
                company_id=company_id,
            )
            blob_name = blob_result["blob_name"]
            blob_url = blob_result["url"]
            signed_url = blob_result["signed_url"]
            signed_url_expiry = datetime.utcnow() + timedelta(hours=24)
            logger.info(f"[Upload] Uploaded to blob: {blob_name}")
        except Exception as e:
            logger.error(f"[Upload] Failed to upload to blob storage: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
    else:
        logger.warning("[Upload] Blob storage not configured, using local storage")

    # Save file locally for processing (temporary)
    doc_processor = DocumentProcessor()
    file_path = doc_processor.save_uploaded_file(
        file_content=content,
        filename=file.filename,
        tenant_id=user.tenant_id
    )

    # Detect content type
    ext = Path(file.filename).suffix.lower()
    content_type = blob_storage._get_content_type(ext) if blob_storage else None

    # Create document record
    document = Document(
        tenant_id=user.tenant_id,
        company_id=company_id,
        uploaded_by=user.id,
        filename=Path(file_path).name,
        original_filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        file_path=file_path,
        # Blob storage fields
        blob_name=blob_name,
        blob_url=blob_url,
        signed_url=signed_url,
        signed_url_expiry=signed_url_expiry,
        content_type=content_type,
        status=DocumentStatus.PENDING,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    logger.info(f"[Upload] Document created: {document.id}")

    # Send message to processing queue (triggers Azure Function)
    queue_service = get_queue_service()
    if queue_service.is_configured() and blob_name:
        queue_sent = queue_service.send_document_processing_message(
            document_id=document.id,
            blob_name=blob_name,
            tenant_id=user.tenant_id,
            company_id=company_id,
            filename=file.filename,
        )
        if queue_sent:
            logger.info(f"[Upload] Document queued for processing: {document.id}")
        else:
            logger.error(f"[Upload] Failed to queue document for processing: {document.id}")
            # Update document status to failed
            document.status = DocumentStatus.FAILED
            document.error_message = "Failed to queue document for processing"
            session.add(document)
            session.commit()
            raise HTTPException(status_code=500, detail="Failed to queue document for processing")
    else:
        logger.warning("[Upload] Queue service not configured, document will not be processed automatically")

    # Register document for WebSocket progress tracking
    ws_manager.register_document(document.id, user.tenant_id)

    # Clean up local file immediately since Azure Function will download from blob
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[Upload] Cleaned up temporary local file: {file_path}")
    except Exception as e:
        logger.warning(f"[Upload] Failed to clean up local file: {e}")

    return UploadResponse(
        document_id=document.id,
        filename=file.filename,
        status=document.status,
        message="Document uploaded successfully. Processing will start automatically."
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[DocumentStatus] = None,
    file_type: Optional[DocumentType] = None,
    company_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """List all documents for the current tenant, optionally filtered by company."""
    query = select(Document).where(Document.tenant_id == user.tenant_id)

    if status:
        query = query.where(Document.status == status)
    if file_type:
        query = query.where(Document.file_type == file_type)
    if company_id:
        query = query.where(Document.company_id == company_id)

    # Get total count
    count_query = select(func.count(Document.id)).where(Document.tenant_id == user.tenant_id)
    if status:
        count_query = count_query.where(Document.status == status)
    if file_type:
        count_query = count_query.where(Document.file_type == file_type)
    if company_id:
        count_query = count_query.where(Document.company_id == company_id)
    total = session.exec(count_query).one()

    # Get paginated results
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    documents = session.exec(query).all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentWithChunksResponse)
async def get_document(
    document_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get a document with its chunks."""
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get chunks
    chunks = session.exec(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all()

    chunk_responses = []
    for chunk in chunks:
        chunk_dict = {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "summary": chunk.summary,
            "previous_context": chunk.previous_context,
            "pillar": chunk.pillar,
            "chunk_type": chunk.chunk_type,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "confidence_score": chunk.confidence_score,
            "metadata": json.loads(chunk.metadata_json) if chunk.metadata_json else None,
            "created_at": chunk.created_at,
        }
        chunk_responses.append(ChunkResponse.model_validate(chunk_dict))

    return DocumentWithChunksResponse(
        document=DocumentResponse.model_validate(document),
        chunks=chunk_responses,
        chunk_count=len(chunks)
    )


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
async def get_document_status(
    document_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get the processing status of a document."""
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get chunk count
    chunk_count = session.exec(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
    ).one()

    return ProcessingStatusResponse(
        document_id=document.id,
        status=document.status,
        total_pages=document.total_pages,
        processed_pages=document.processed_pages,
        error_message=document.error_message,
        chunk_count=chunk_count
    )


@router.get("/{document_id}/progress")
async def get_document_progress(
    document_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """
    Get the cached processing progress for a document.
    Returns the last known progress state from Redis cache.
    Useful for restoring progress display when user returns to the page.
    """
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get cached progress from Redis
    cached_progress = await ws_manager.get_cached_progress(document_id)

    if cached_progress:
        return {
            "document_id": document_id,
            "has_progress": True,
            **cached_progress
        }

    # No cached progress - return current status from database
    return {
        "document_id": document_id,
        "has_progress": False,
        "status": document.status.value,
        "step": 6 if document.status == DocumentStatus.COMPLETED else (0 if document.status == DocumentStatus.PENDING else None),
        "step_name": "Completed" if document.status == DocumentStatus.COMPLETED else ("Pending" if document.status == DocumentStatus.PENDING else "Processing"),
        "progress": 100 if document.status == DocumentStatus.COMPLETED else 0,
    }


@router.post("/progress/batch")
async def get_documents_progress_batch(
    document_ids: List[str],
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """
    Get cached processing progress for multiple documents.
    Efficient batch retrieval for restoring progress display.
    """
    logger.info(f"[Progress] Batch progress request for {len(document_ids)} document(s): {document_ids}")

    # Verify user has access to all documents
    results = {}

    for doc_id in document_ids:
        document = session.get(Document, doc_id)
        if document and document.tenant_id == user.tenant_id:
            results[doc_id] = {
                "status": document.status.value,
                "total_pages": document.total_pages,
                "processed_pages": document.processed_pages,
            }
            logger.info(f"[Progress] Document {doc_id}: status={document.status.value}")

    # Get cached progress from Redis for all documents
    cached_progress = await ws_manager.get_cached_progress_batch(document_ids)
    logger.info(f"[Progress] Retrieved cached progress for {len(cached_progress)} document(s)")

    # Merge cached progress with database status
    for doc_id, progress in cached_progress.items():
        if doc_id in results:
            results[doc_id]["cached_progress"] = progress
            logger.info(f"[Progress] Cached progress for {doc_id}: step={progress.get('step')}, progress={progress.get('progress')}%")

    return {"progress": results}


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    pillar: Optional[BDEPillar] = None,
    chunk_type: Optional[ChunkType] = None,
    page_number: Optional[int] = None,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get chunks for a document with optional filtering."""
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)

    if pillar:
        query = query.where(DocumentChunk.pillar == pillar)
    if chunk_type:
        query = query.where(DocumentChunk.chunk_type == chunk_type)
    if page_number:
        query = query.where(DocumentChunk.page_number == page_number)

    query = query.order_by(DocumentChunk.chunk_index)
    chunks = session.exec(query).all()

    chunk_responses = []
    for chunk in chunks:
        chunk_dict = {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "content": chunk.content,
            "summary": chunk.summary,
            "previous_context": chunk.previous_context,
            "pillar": chunk.pillar,
            "chunk_type": chunk.chunk_type,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "confidence_score": chunk.confidence_score,
            "metadata": json.loads(chunk.metadata_json) if chunk.metadata_json else None,
            "created_at": chunk.created_at,
        }
        chunk_responses.append(ChunkResponse.model_validate(chunk_dict))

    return chunk_responses


@router.get("/{document_id}/download")
async def get_document_download_url(
    document_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get a signed URL to download/preview a document."""
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not document.blob_name:
        raise HTTPException(status_code=404, detail="Document file not available")

    # Check if we have a valid signed URL
    if document.signed_url and document.signed_url_expiry:
        if document.signed_url_expiry > datetime.utcnow():
            return {
                "download_url": document.signed_url,
                "filename": document.original_filename,
                "content_type": document.content_type,
            }

    # Generate a new signed URL
    blob_storage = get_blob_storage_client()
    if not blob_storage.is_configured():
        raise HTTPException(status_code=500, detail="Storage not configured")

    try:
        signed_url = blob_storage.get_signed_url(document.blob_name, expiry_hours=24)

        # Update the document with the new signed URL
        document.signed_url = signed_url
        document.signed_url_expiry = datetime.utcnow() + timedelta(hours=24)
        session.add(document)
        session.commit()

        return {
            "download_url": signed_url,
            "filename": document.original_filename,
            "content_type": document.content_type,
        }
    except Exception as e:
        logger.error(f"[Download] Failed to generate signed URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: User = Depends(require_permission(Permissions.FILES_DELETE)),
    session: Session = Depends(get_session),
):
    """Delete a document and its chunks."""
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"[Delete] Deleting document: {document_id}")

    # Store blob_name before deletion for cleanup
    blob_name = document.blob_name
    file_path = document.file_path

    # Delete chunks first
    chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()

    logger.info(f"[Delete] Removing {len(chunks)} chunks")
    for chunk in chunks:
        session.delete(chunk)

    # Commit chunk deletions first to satisfy foreign key constraint
    session.commit()

    # Now delete document
    session.delete(document)
    session.commit()

    # Try to delete from blob storage
    if blob_name:
        try:
            blob_storage = get_blob_storage_client()
            if blob_storage.is_configured():
                deleted = blob_storage.delete_file(blob_name)
                if deleted:
                    logger.info(f"[Delete] Blob removed: {blob_name}")
                else:
                    logger.warning(f"[Delete] Blob not found: {blob_name}")
        except Exception as e:
            logger.warning(f"[Delete] Failed to remove blob: {e}")

    # Try to delete local file (if exists)
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[Delete] Local file removed: {file_path}")
    except Exception as e:
        logger.warning(f"[Delete] Failed to remove local file: {e}")

    logger.info(f"[Delete] Document deleted successfully")
    return {"message": "Document deleted successfully"}


@router.post("/webhook/status")
async def webhook_status_update(
    payload: WebhookPayload,
    x_webhook_secret: Optional[str] = Header(None),
    session: Session = Depends(get_session),
):
    """
    Webhook endpoint for Azure Function to notify processing status/progress.
    Called at each processing step and when completed/failed.
    """
    # Validate webhook secret if configured
    if WEBHOOK_SECRET:
        if x_webhook_secret != WEBHOOK_SECRET:
            logger.warning(f"[Webhook] Invalid or missing webhook secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    logger.info(f"[Webhook] Received status update for document: {payload.document_id}")
    logger.info(f"  Status: {payload.status}, Step: {payload.step}, Progress: {payload.progress}%")

    # Get the document to find tenant_id for WebSocket routing
    document = session.get(Document, payload.document_id)
    if not document:
        logger.error(f"[Webhook] Document not found: {payload.document_id}")
        raise HTTPException(status_code=404, detail="Document not found")

    # Broadcast progress via WebSocket
    step = payload.step or 1
    step_name = payload.step_name or PROCESSING_STEPS.get(step, {}).get("name", "Processing")
    progress = payload.progress or PROCESSING_STEPS.get(step, {}).get("progress", 0)

    await ws_manager.broadcast_progress(
        document_id=payload.document_id,
        step=step,
        step_name=step_name,
        progress=progress,
        status=payload.status,
        error_message=payload.error_message
    )

    # Log additional details for completed/failed and clear cached progress
    if payload.status == "completed":
        logger.info(f"  Total pages: {payload.total_pages}")
        logger.info(f"  Processed pages: {payload.processed_pages}")
        logger.info(f"  Chunks count: {payload.chunks_count}")
        if payload.usage_stats:
            logger.info(f"  Token usage: {payload.usage_stats.get('total_tokens', 0):,}")
        # Unregister document from WebSocket tracking and clear cached progress
        ws_manager.unregister_document(payload.document_id)
        await ws_manager.clear_cached_progress(payload.document_id)
    elif payload.status == "failed":
        logger.error(f"  Error: {payload.error_message}")
        # Unregister document from WebSocket tracking and clear cached progress
        ws_manager.unregister_document(payload.document_id)
        await ws_manager.clear_cached_progress(payload.document_id)

    return {
        "message": "Webhook received",
        "document_id": payload.document_id,
        "status": payload.status
    }


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time document processing progress.
    Client sends tenant_id after connection to subscribe to updates.
    """
    tenant_id = None
    try:
        await websocket.accept()
        data = await websocket.receive_json()
        tenant_id = data.get("tenant_id")

        if not tenant_id:
            await websocket.close(code=4001, reason="tenant_id required")
            return

        # Register connection
        async with ws_manager._lock:
            if tenant_id not in ws_manager._connections:
                ws_manager._connections[tenant_id] = set()
            ws_manager._connections[tenant_id].add(websocket)
        logger.info(f"[WebSocket] Connection established for tenant: {tenant_id}")

        # Keep connection alive with ping/pong
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0
                )
                if message.get("type") == "pong":
                    continue
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected: {tenant_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Error: {e}")
    finally:
        if tenant_id:
            await ws_manager.disconnect(websocket, tenant_id)


# =============================================================================
# TEST ENDPOINT: Process document using unified ChunkingService locally
# =============================================================================

@router.post("/test/process-local")
async def test_process_document_local(
    file: UploadFile = File(...),
    company_id: str = Form(...),
    user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
    session: Session = Depends(get_session),
):
    """
    TEST ENDPOINT: Upload and process a document locally using the unified ChunkingService.

    This bypasses Azure Function and processes the document directly in the web server.
    Use this to test the unified chunking pipeline before moving to Azure Function.

    Returns the document with all generated chunks.
    """
    logger.info(f"[TestProcessLocal] === Starting local document processing ===")
    logger.info(f"[TestProcessLocal] File: {file.filename}")
    logger.info(f"[TestProcessLocal] Company ID: {company_id}")

    start_time = time.time()

    # Validate company
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    all_allowed = ALLOWED_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS
    if ext not in all_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(sorted(all_allowed))}"
        )

    # Read file content
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    logger.info(f"[TestProcessLocal] File size: {file_size_mb:.2f} MB")

    # Get file type
    try:
        file_type = get_file_type(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save file locally
    doc_processor = DocumentProcessor()
    file_path = doc_processor.save_uploaded_file(
        file_content=content,
        filename=file.filename,
        tenant_id=user.tenant_id
    )

    # Create document record
    document = Document(
        tenant_id=user.tenant_id,
        company_id=company_id,
        uploaded_by=user.id,
        filename=Path(file_path).name,
        original_filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        file_path=file_path,
        status=DocumentStatus.PROCESSING,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    logger.info(f"[TestProcessLocal] Document created: {document.id}")

    try:
        # Step 1: Convert document to pages
        logger.info(f"[TestProcessLocal] Step 1: Converting document to pages...")
        pages = doc_processor.process_document(file_path, file_type.value)
        logger.info(f"[TestProcessLocal] Converted to {len(pages)} pages")

        # Update document with page count
        document.total_pages = len(pages)
        session.add(document)
        session.commit()

        # Step 2: Process through unified ChunkingService
        logger.info(f"[TestProcessLocal] Step 2: Processing through ChunkingService...")
        chunking_service = get_chunking_service()

        chunk_input = ChunkInput(
            source_type=SourceType.DOCUMENT,
            tenant_id=user.tenant_id,
            company_id=company_id,
            document_id=document.id,
            pages=pages,
            document_filename=file.filename,
        )

        result = await chunking_service.process(chunk_input)

        logger.info(f"[TestProcessLocal] ChunkingService returned {len(result.chunks)} chunks")
        logger.info(f"[TestProcessLocal] Usage stats: {result.usage_stats}")

        # Step 3: Save chunks to database
        logger.info(f"[TestProcessLocal] Step 3: Saving chunks to database...")
        chunks_saved = 0
        for chunk_output in result.chunks:
            db_chunk = DocumentChunk(
                document_id=document.id,
                tenant_id=user.tenant_id,
                company_id=company_id,
                content=chunk_output.content,
                summary=chunk_output.summary,
                pillar=chunk_output.pillar,
                chunk_type=chunk_output.chunk_type,
                page_number=chunk_output.page_number or 0,
                chunk_index=chunk_output.chunk_index or 0,
                confidence_score=chunk_output.confidence_score,
                metadata_json=json.dumps(chunk_output.metadata) if chunk_output.metadata else None,
                previous_context=chunk_output.previous_context,
                embedding=chunk_output.embedding,
            )
            session.add(db_chunk)
            chunks_saved += 1

        # Update document status and overview
        document.status = DocumentStatus.COMPLETED
        document.processed_pages = len(pages)
        document.document_type = result.overview.get("document_type")
        document.document_title = result.overview.get("title")
        document.document_summary = result.overview.get("summary")
        document.key_themes = json.dumps(result.overview.get("key_themes", []))
        session.add(document)
        session.commit()

        logger.info(f"[TestProcessLocal] Saved {chunks_saved} chunks to database")

        # Clean up local file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"[TestProcessLocal] Failed to clean up local file: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"[TestProcessLocal] === Processing complete in {elapsed_time:.2f}s ===")

        # Return result
        return {
            "success": True,
            "document_id": document.id,
            "filename": file.filename,
            "total_pages": len(pages),
            "chunks_created": chunks_saved,
            "usage_stats": result.usage_stats,
            "overview": result.overview,
            "elapsed_time_seconds": round(elapsed_time, 2),
        }

    except Exception as e:
        logger.error(f"[TestProcessLocal] Processing failed: {e}", exc_info=True)

        # Update document status to failed
        document.status = DocumentStatus.FAILED
        document.error_message = str(e)[:500]
        session.add(document)
        session.commit()

        # Clean up local file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )
