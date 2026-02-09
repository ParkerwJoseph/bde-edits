import json
import os
import time
import asyncio
import httpx
from datetime import datetime
import sys

# File-based logging for debugging Azure Functions critical issues
# ALWAYS enabled to diagnose intermittent failures
DEBUG_LOG_FILE = "/tmp/azure_function_debug.log"

def debug_log(message: str):
    """Write debug message to file with timestamp - ALWAYS logs for debugging."""
    try:
        timestamp = datetime.now().isoformat()
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
            f.flush()
    except Exception:
        pass

import azure.functions as func
from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy

# Log immediately when module is imported
debug_log("=" * 70)
debug_log("FUNCTION_APP.PY MODULE LOADING")
debug_log(f"Python: {sys.version}")
debug_log(f"CWD: {os.getcwd()}")
debug_log("=" * 70)


def run_async(coro):
    """
    Run an async coroutine safely, handling cases where an event loop may already be running.
    This prevents 'asyncio.run() cannot be called from a running event loop' errors
    when Azure Functions processes multiple queue messages concurrently.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Loop is already running - create a new loop in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

from shared.database.connection import get_db_session
from shared.database.models import (
    Document, DocumentStatus, DocumentChunk, BDEPillar, ChunkType,
)
from shared.services.document_processor import DocumentProcessor
from shared.services.chunking import get_chunking_service, ChunkInput, SourceType
from shared.services.storage.blob_storage import get_blob_storage_client
from shared.config.settings import (
    FASTAPI_WEBHOOK_URL,
    WEBHOOK_SECRET,
    UPLOAD_DIR,
    AZURE_STORAGE_CONNECTION_STRING,
    DOCUMENT_PROCESSING_QUEUE,
    QUICKBOOK_PROCESSING_QUEUE,
    QUICKBOOK_WEBHOOK_URL,
    CARBONVOICE_PROCESSING_QUEUE,
    CARBONVOICE_WEBHOOK_URL,
)

# Max retry cycles before permanently failing (each cycle = 5 dequeue attempts)
MAX_RETRY_CYCLES = 3
# Delay before re-queued message becomes visible (in seconds) - 10 minutes
REQUEUE_DELAY_SECONDS = 600
# Maximum total processing time per document (in seconds) - 3 hours
# This is less than the 4-hour function timeout to allow graceful handling
MAX_DOCUMENT_PROCESSING_SECONDS = 3 * 60 * 60  # 3 hours
# Heartbeat interval for logging during long operations (in seconds)
HEARTBEAT_INTERVAL_SECONDS = 60


class ProcessingTimeoutError(Exception):
    """Raised when document processing exceeds the maximum allowed time."""
    pass


def check_processing_timeout(start_time: float, document_id: str, current_step: str) -> None:
    """
    Check if processing has exceeded the maximum allowed time.

    Args:
        start_time: Unix timestamp when processing started
        document_id: Document ID for logging
        current_step: Current processing step name for logging

    Raises:
        ProcessingTimeoutError: If processing time exceeds MAX_DOCUMENT_PROCESSING_SECONDS
    """
    elapsed = time.time() - start_time
    if elapsed > MAX_DOCUMENT_PROCESSING_SECONDS:
        raise ProcessingTimeoutError(
            f"Document {document_id} processing exceeded {MAX_DOCUMENT_PROCESSING_SECONDS}s "
            f"(elapsed: {elapsed:.0f}s) during step: {current_step}"
        )
from shared.utils.logger import get_logger

logger = get_logger(__name__)

app = func.FunctionApp()

# Log queue configuration on startup
logger.info("=" * 70)
logger.info("[STARTUP] Azure Functions Queue Configuration")
logger.info(f"  DOCUMENT_PROCESSING_QUEUE: {DOCUMENT_PROCESSING_QUEUE}")
logger.info(f"  QUICKBOOK_PROCESSING_QUEUE: {QUICKBOOK_PROCESSING_QUEUE}")
logger.info(f"  CARBONVOICE_PROCESSING_QUEUE: {CARBONVOICE_PROCESSING_QUEUE}")
logger.info(f"  AzureWebJobsStorage configured: {bool(os.getenv('AzureWebJobsStorage'))}")
logger.info("=" * 70)


# =============================================================================
# Queue Trigger - Document processing
# =============================================================================
# NOTE: Messages are sent directly from the FastAPI upload endpoint.
# This avoids blob trigger issues with large files where the Azure Functions
# runtime fails to bind the InputStream before the function code executes.
# =============================================================================
@app.queue_trigger(
    arg_name="msg",
    queue_name="%DOCUMENT_PROCESSING_QUEUE%",
    connection="AzureWebJobsStorage"
)
def process_document_queue(msg: func.QueueMessage):
    """
    Queue-triggered function for document processing.
    Handles the full processing pipeline without timeout concerns.
    Queue visibility timeout auto-extends for running functions.
    """
    # DEBUG: Log to file immediately on function entry
    debug_log("=" * 70)
    debug_log(f"[ProcessDocument] FUNCTION TRIGGERED")
    debug_log(f"[ProcessDocument] Message ID: {msg.id}")
    debug_log(f"[ProcessDocument] Dequeue count: {msg.dequeue_count}")
    debug_log(f"[ProcessDocument] Insertion time: {msg.insertion_time}")
    debug_log("=" * 70)

    logger.info("=" * 70)
    logger.info(f"[ProcessDocument] FUNCTION TRIGGERED - Message received")
    logger.info(f"[ProcessDocument] Dequeue count: {msg.dequeue_count}")
    logger.info(f"[ProcessDocument] Message ID: {msg.id}")
    logger.info("=" * 70)

    # Wrap message parsing in try-except to catch any initialization issues
    try:
        debug_log("[ProcessDocument] Parsing message body...")
        message_body = msg.get_body().decode('utf-8')
        debug_log(f"[ProcessDocument] Raw message: {message_body[:200]}")
        logger.info(f"[ProcessDocument] Raw message body: {message_body[:500]}")
        message_data = json.loads(message_body)

        document_id = message_data.get("document_id")
        blob_name = message_data.get("blob_name")
        retry_cycle = message_data.get("retry_cycle", 1)  # Track which retry cycle we're on
        debug_log(f"[ProcessDocument] Parsed: doc_id={document_id}, blob={blob_name}")
    except Exception as e:
        debug_log(f"[ProcessDocument] PARSE ERROR: {type(e).__name__}: {e}")
        logger.error(f"[ProcessDocument] CRITICAL: Failed to parse queue message: {type(e).__name__}: {e}")
        logger.error(f"[ProcessDocument] Message body: {msg.get_body()}")
        import traceback
        logger.error(f"[ProcessDocument] Traceback: {traceback.format_exc()}")
        raise  # Re-raise to trigger queue retry

    debug_log(f"[ProcessDocument] Starting processing for {document_id}")
    logger.info(f"[ProcessDocument] Starting processing")
    logger.info(f"  Document ID: {document_id}")
    logger.info(f"  Blob name: {blob_name}")
    logger.info(f"  Retry cycle: {retry_cycle}/{MAX_RETRY_CYCLES}")
    logger.info(f"  Insertion time: {msg.insertion_time}")
    logger.info("=" * 70)

    start_time = time.time()
    session = None
    document = None
    local_file_path = None

    try:
        # === STEP 0: Database Connection with retry ===
        debug_log(f"[ProcessDocument] STEP 0: Connecting to database...")
        logger.info(f"[ProcessDocument] STEP 0: Connecting to database...")
        step0_start = time.time()

        max_db_retries = 3
        db_retry_delay = 2
        db_last_error = None

        for db_attempt in range(1, max_db_retries + 1):
            try:
                debug_log(f"[ProcessDocument] DB attempt {db_attempt}/{max_db_retries}")
                logger.info(f"[ProcessDocument] Database connection attempt {db_attempt}/{max_db_retries}")
                session = get_db_session()

                # Test the connection by executing a simple query
                from sqlmodel import select, text
                session.exec(text("SELECT 1"))

                debug_log(f"[ProcessDocument] DB connected in {time.time() - step0_start:.2f}s")
                logger.info(f"[ProcessDocument] STEP 0: Database connected in {time.time() - step0_start:.2f}s")
                break  # Success

            except Exception as e:
                db_last_error = e
                debug_log(f"[ProcessDocument] DB attempt {db_attempt} FAILED: {type(e).__name__}: {e}")
                logger.warning(f"[ProcessDocument] Database connection attempt {db_attempt} failed: {type(e).__name__}: {e}")
                if session:
                    try:
                        session.close()
                    except:
                        pass
                    session = None

                if db_attempt < max_db_retries:
                    logger.info(f"[ProcessDocument] Retrying database connection in {db_retry_delay}s...")
                    time.sleep(db_retry_delay)
                    db_retry_delay *= 2
                else:
                    logger.error(f"[ProcessDocument] Failed to connect to database after {max_db_retries} attempts")
                    raise db_last_error

        from sqlmodel import select
        statement = select(Document).where(Document.id == document_id)
        document = session.exec(statement).first()

        if not document:
            logger.error(f"[ProcessDocument] Document not found: {document_id}")
            return  # Don't retry if document doesn't exist

        logger.info(f"[ProcessDocument] Processing document: {document.original_filename}")
        logger.info(f"  File type: {document.file_type}")
        logger.info(f"  Blob name: {blob_name}")

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        document.updated_at = datetime.utcnow()
        session.add(document)
        session.commit()
        logger.info(f"[ProcessDocument] Status updated to PROCESSING")

        # === STEP 1: Download blob to local file ===
        check_processing_timeout(start_time, document_id, "before download")
        logger.info(f"[ProcessDocument] ========================================")
        logger.info(f"[ProcessDocument] STEP 1: Starting file download...")
        logger.info(f"[ProcessDocument] ========================================")
        _send_progress_webhook(document.id, step=1, step_name="Downloading File", progress=5)

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        logger.info(f"[ProcessDocument] Upload directory ready: {UPLOAD_DIR}")

        ext = os.path.splitext(document.original_filename)[1].lower()
        local_file_path = os.path.join(UPLOAD_DIR, f"{document.id}{ext}")

        logger.info(f"[ProcessDocument] Downloading blob...")
        logger.info(f"[ProcessDocument]   From: {blob_name}")
        logger.info(f"[ProcessDocument]   To: {local_file_path}")

        download_start = time.time()
        max_download_retries = 5  # Increased retries for intermittent connection issues
        download_retry_delay = 3  # seconds between retries (starts smaller)
        last_error = None

        for download_attempt in range(1, max_download_retries + 1):
            try:
                logger.info(f"[ProcessDocument] Download attempt {download_attempt}/{max_download_retries}")
                # ALWAYS force new client to ensure fresh connection
                # This is critical for avoiding stale connection issues in Azure Functions
                blob_client = get_blob_storage_client(force_new=True)
                blob_client.download_file(blob_name, local_file_path, timeout_seconds=120)
                download_time = time.time() - download_start
                file_size = os.path.getsize(local_file_path)
                logger.info(f"[ProcessDocument] STEP 1 COMPLETE: Downloaded {file_size} bytes in {download_time:.2f}s")
                break  # Success, exit retry loop

            except FileNotFoundError as e:
                # Blob doesn't exist - no point retrying
                logger.error(f"[ProcessDocument] STEP 1 FAILED: Blob not found - {e}")
                raise

            except ConnectionError as e:
                # Connection errors are most likely to be transient - definitely retry
                last_error = e
                logger.warning(f"[ProcessDocument] Download attempt {download_attempt} - CONNECTION ERROR: {e}")
                logger.warning(f"[ProcessDocument] This is usually a transient issue, will retry...")

                if download_attempt < max_download_retries:
                    logger.info(f"[ProcessDocument] Waiting {download_retry_delay}s before retry...")
                    time.sleep(download_retry_delay)
                    download_retry_delay = min(download_retry_delay * 2, 30)  # Cap at 30 seconds
                else:
                    logger.error(f"[ProcessDocument] STEP 1 FAILED: All {max_download_retries} download attempts failed due to connection errors")
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[ProcessDocument] Download attempt {download_attempt} failed: {type(e).__name__}: {e}")

                if download_attempt < max_download_retries:
                    logger.info(f"[ProcessDocument] Retrying download in {download_retry_delay}s...")
                    time.sleep(download_retry_delay)
                    download_retry_delay = min(download_retry_delay * 2, 30)  # Cap at 30 seconds
                else:
                    # All retries exhausted
                    logger.error(f"[ProcessDocument] STEP 1 FAILED: All {max_download_retries} download attempts failed")
                    import traceback
                    logger.error(f"[ProcessDocument] Traceback:\n{traceback.format_exc()}")
                    raise

        # === STEP 2: Analyze document (convert to pages) ===
        check_processing_timeout(start_time, document_id, "before document analysis")
        logger.info(f"[ProcessDocument] ========================================")
        logger.info(f"[ProcessDocument] STEP 2: Converting document to pages...")
        logger.info(f"[ProcessDocument] ========================================")
        _send_progress_webhook(document.id, step=2, step_name="Analyzing Document", progress=15)

        try:
            doc_processor = DocumentProcessor()
            step2_start = time.time()
            pages = doc_processor.process_document(local_file_path, document.file_type.value)
            step2_time = time.time() - step2_start
            logger.info(f"[ProcessDocument] STEP 2 COMPLETE: {len(pages)} pages in {step2_time:.2f}s")
        except Exception as e:
            logger.error(f"[ProcessDocument] STEP 2 FAILED: Conversion error - {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[ProcessDocument] Traceback:\n{traceback.format_exc()}")
            raise

        document.total_pages = len(pages)
        session.add(document)
        session.commit()

        # === STEP 3: LLM analysis using ChunkingService ===
        check_processing_timeout(start_time, document_id, "before LLM analysis")
        logger.info(f"[ProcessDocument] ========================================")
        logger.info(f"[ProcessDocument] STEP 3: Starting LLM analysis...")
        logger.info(f"[ProcessDocument] ========================================")
        _send_progress_webhook(document.id, step=3, step_name="Creating Chunks", progress=35)

        step3_start = time.time()

        # Create ChunkInput for document processing
        chunking_service = get_chunking_service()
        chunk_input = ChunkInput(
            source_type=SourceType.DOCUMENT,
            tenant_id=str(document.tenant_id),
            company_id=str(document.company_id),
            document_id=str(document.id),
            pages=pages,
            document_filename=document.original_filename,
        )

        # Create progress callback for per-page updates with timeout check and heartbeat
        # Progress during chunking: 35% to 65% (30% range spread across pages)
        last_heartbeat_time = [start_time]  # Use list to allow mutation in nested function

        def chunking_progress_callback(current_page: int, total_pages: int, step_name: str):
            # Check for processing timeout
            check_processing_timeout(start_time, document_id, f"LLM analysis page {current_page}/{total_pages}")

            # Heartbeat logging for long-running operations
            current_time = time.time()
            if current_time - last_heartbeat_time[0] >= HEARTBEAT_INTERVAL_SECONDS:
                elapsed = current_time - start_time
                logger.info(f"[ProcessDocument] HEARTBEAT: Document {document_id} still processing - "
                           f"page {current_page}/{total_pages}, elapsed: {elapsed:.0f}s")
                last_heartbeat_time[0] = current_time

            # Calculate progress: 35% + (current_page / total_pages) * 30%
            progress = 35 + int((current_page / total_pages) * 30)
            _send_progress_webhook(
                document.id,
                step=3,
                step_name=f"Creating Chunks ({current_page}/{total_pages})",
                progress=progress
            )

        # Process through ChunkingService (handles LLM + embeddings)
        # Use run_async to safely handle concurrent queue processing
        result = run_async(chunking_service.process(chunk_input, chunking_progress_callback))

        step2_time = time.time() - step2_start
        logger.info(f"[ProcessDocument] ChunkingService completed in {step2_time:.2f}s")

        all_chunks = result.chunks
        document_overview = result.overview
        usage_stats = result.usage_stats

        # Update document with overview
        document.document_type = document_overview.get("document_type")
        document.document_title = document_overview.get("title")
        document.document_summary = document_overview.get("summary")
        document.key_themes = json.dumps(document_overview.get("key_themes", []))
        document.overview_json = json.dumps(document_overview)
        session.add(document)
        session.commit()

        logger.info(f"[ProcessDocument] Saved document overview")

        # Step 4: Embeddings already generated by ChunkingService
        check_processing_timeout(start_time, document_id, "after LLM analysis")
        _send_progress_webhook(document.id, step=4, step_name="Generating Embeddings", progress=65)
        logger.info(f"[ProcessDocument] Embeddings already generated by ChunkingService")

        # Step 5: Store results (with idempotency - delete existing chunks first)
        check_processing_timeout(start_time, document_id, "before storing results")
        _send_progress_webhook(document.id, step=5, step_name="Storing Results", progress=85)

        # Delete any existing chunks for this document (idempotency for retries)
        from sqlmodel import delete
        existing_chunks_stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        session.exec(existing_chunks_stmt)
        session.commit()
        logger.info(f"[ProcessDocument] Cleared existing chunks for idempotency")

        # Save new chunks from ChunkOutput objects
        for idx, chunk_output in enumerate(all_chunks):
            content = chunk_output.content
            if isinstance(content, (dict, list)):
                content = json.dumps(content)

            chunk = DocumentChunk(
                document_id=document.id,
                tenant_id=document.tenant_id,
                company_id=document.company_id,
                content=content,
                summary=chunk_output.summary,
                previous_context=chunk_output.previous_context,
                pillar=BDEPillar(chunk_output.pillar),
                chunk_type=ChunkType(chunk_output.chunk_type),
                page_number=chunk_output.page_number or 1,
                chunk_index=chunk_output.chunk_index or idx,
                confidence_score=chunk_output.confidence_score,
                metadata_json=json.dumps(chunk_output.metadata) if chunk_output.metadata else None,
                embedding=chunk_output.embedding
            )
            session.add(chunk)

        # Mark document as completed
        total_time = time.time() - start_time
        document.status = DocumentStatus.COMPLETED
        document.processed_pages = document.total_pages
        document.error_message = None  # Clear any previous error
        document.updated_at = datetime.utcnow()
        session.add(document)
        session.commit()

        logger.info("=" * 70)
        logger.info(f"[ProcessDocument] DOCUMENT PROCESSING COMPLETED")
        logger.info(f"  Document: {document.original_filename}")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Pages processed: {document.total_pages}")
        logger.info(f"  Chunks extracted: {len(all_chunks)}")
        logger.info(f"  Token usage: {usage_stats.get('total_tokens', 0):,}")
        logger.info("=" * 70)

        # Step 6: Send completion webhook
        _send_webhook_notification(
            document_id=document.id,
            status="completed",
            step=6,
            step_name="Completed",
            progress=100,
            total_pages=document.total_pages,
            processed_pages=document.processed_pages,
            chunks_count=len(all_chunks),
            usage_stats=usage_stats
        )

    except ProcessingTimeoutError as e:
        # Special handling for processing timeout - don't retry, fail immediately
        total_time = time.time() - start_time
        error_message = str(e)[:1000]

        logger.error(f"[ProcessDocument] PROCESSING TIMEOUT after {total_time:.2f}s")
        logger.error(f"  Error: {error_message}")

        if session and document:
            try:
                document.status = DocumentStatus.FAILED
                document.error_message = f"Processing timeout: Document took too long to process. {error_message}"
                document.updated_at = datetime.utcnow()
                session.add(document)
                session.commit()

                _send_webhook_notification(
                    document_id=document.id,
                    status="failed",
                    error_message=f"Processing timeout after {total_time:.0f}s"
                )
            except Exception as db_error:
                logger.error(f"[ProcessDocument] Failed to update document status: {db_error}")

        # Don't re-raise - timeout errors should not trigger retry
        return

    except ConnectionError as e:
        # Special handling for connection errors - these may be transient, allow retry
        total_time = time.time() - start_time
        error_message = str(e)[:1000]

        logger.error(f"[ProcessDocument] CONNECTION ERROR after {total_time:.2f}s")
        logger.error(f"  Error: {error_message}")
        logger.error(f"  Dequeue count: {msg.dequeue_count}")
        logger.error(f"  Retry cycle: {retry_cycle}/{MAX_RETRY_CYCLES}")

        if session and document:
            try:
                document.error_message = f"Connection error (will retry): {error_message[:200]}"
                document.updated_at = datetime.utcnow()
                session.add(document)
                session.commit()
            except Exception as db_error:
                logger.error(f"[ProcessDocument] Failed to update document status: {db_error}")

        # Re-raise to trigger queue retry
        raise

    except Exception as e:
        total_time = time.time() - start_time
        error_message = str(e)[:1000]

        logger.error(f"[ProcessDocument] PROCESSING FAILED after {total_time:.2f}s")
        logger.error(f"  Error: {error_message}")
        logger.error(f"  Dequeue count: {msg.dequeue_count}")
        logger.error(f"  Retry cycle: {retry_cycle}/{MAX_RETRY_CYCLES}")

        import traceback
        logger.error(traceback.format_exc())

        if session and document:
            try:
                # On final dequeue attempt of current cycle
                if msg.dequeue_count >= 5:
                    if retry_cycle < MAX_RETRY_CYCLES:
                        # Re-queue with incremented retry cycle
                        _requeue_document(message_data, retry_cycle + 1)
                        logger.info(f"[ProcessDocument] Re-queued for retry cycle {retry_cycle + 1}/{MAX_RETRY_CYCLES}")

                        # Update document status to show it's waiting for retry
                        document.status = DocumentStatus.PENDING
                        document.error_message = f"Retry cycle {retry_cycle} failed: {error_message[:200]}. Waiting for retry."
                        document.updated_at = datetime.utcnow()
                        session.add(document)
                        session.commit()

                        # Don't re-raise - we've handled it by re-queuing
                        return
                    else:
                        # Max retry cycles reached - permanently fail
                        document.status = DocumentStatus.FAILED
                        document.error_message = f"Failed after {MAX_RETRY_CYCLES} retry cycles: {error_message}"
                        document.updated_at = datetime.utcnow()
                        session.add(document)
                        session.commit()

                        _send_webhook_notification(
                            document_id=document.id,
                            status="failed",
                            error_message=error_message
                        )
                        logger.error(f"[ProcessDocument] Permanently failed after {MAX_RETRY_CYCLES} retry cycles")
                        return
                else:
                    logger.info(f"[ProcessDocument] Will retry (attempt {msg.dequeue_count}/5 in cycle {retry_cycle})")
            except Exception as db_error:
                logger.error(f"[ProcessDocument] Failed to update document status: {db_error}")

        # Re-raise to trigger queue retry within current cycle
        raise

    finally:
        if session:
            session.close()

        if local_file_path and os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
                logger.info(f"[ProcessDocument] Cleaned up local file: {local_file_path}")
            except Exception as e:
                logger.warning(f"[ProcessDocument] Failed to cleanup file: {e}")


# =============================================================================
# Helper Functions
# =============================================================================
def _requeue_document(message_data: dict, new_retry_cycle: int):
    """
    Re-queue a failed document for another retry cycle.
    Sends a new message with incremented retry_cycle and a visibility delay.
    """
    try:
        queue_client = QueueClient.from_connection_string(
            conn_str=AZURE_STORAGE_CONNECTION_STRING,
            queue_name=DOCUMENT_PROCESSING_QUEUE,
            message_encode_policy=BinaryBase64EncodePolicy(),
        )

        # Create new message with updated retry cycle
        new_message = {
            "document_id": message_data.get("document_id"),
            "blob_name": message_data.get("blob_name"),
            "tenant_id": message_data.get("tenant_id"),
            "company_id": message_data.get("company_id"),
            "filename": message_data.get("filename"),
            "queued_at": datetime.utcnow().isoformat(),
            "retry_cycle": new_retry_cycle,
        }

        message_json = json.dumps(new_message)
        message_bytes = message_json.encode('utf-8')

        # Send with visibility timeout (delay before it becomes visible)
        queue_client.send_message(
            message_bytes,
            visibility_timeout=REQUEUE_DELAY_SECONDS
        )

        logger.info(f"[RequeueDocument] Document {message_data.get('document_id')} re-queued for cycle {new_retry_cycle} with {REQUEUE_DELAY_SECONDS}s delay")

    except Exception as e:
        logger.error(f"[RequeueDocument] Failed to re-queue document: {e}")
        raise


def _send_progress_webhook(
    document_id: str,
    step: int,
    step_name: str,
    progress: int,
    status: str = "processing"
):
    """Send progress webhook to FastAPI backend for real-time UI updates."""
    if not FASTAPI_WEBHOOK_URL:
        return

    payload = {
        "document_id": document_id,
        "status": status,
        "step": step,
        "step_name": step_name,
        "progress": progress,
    }

    headers = {
        "Content-Type": "application/json",
    }
    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(FASTAPI_WEBHOOK_URL, json=payload, headers=headers)
    except Exception as e:
        logger.warning(f"[Webhook] Progress webhook failed: {e}")


def _send_webhook_notification(
    document_id: str,
    status: str,
    step: int = None,
    step_name: str = None,
    progress: int = None,
    total_pages: int = None,
    processed_pages: int = None,
    chunks_count: int = None,
    usage_stats: dict = None,
    error_message: str = None
):
    """Send webhook notification to FastAPI backend."""
    if not FASTAPI_WEBHOOK_URL:
        logger.warning("[Webhook] FASTAPI_WEBHOOK_URL not configured, skipping webhook")
        return

    payload = {
        "document_id": document_id,
        "status": status,
    }

    if step is not None:
        payload["step"] = step
    if step_name is not None:
        payload["step_name"] = step_name
    if progress is not None:
        payload["progress"] = progress
    if total_pages is not None:
        payload["total_pages"] = total_pages
    if processed_pages is not None:
        payload["processed_pages"] = processed_pages
    if chunks_count is not None:
        payload["chunks_count"] = chunks_count
    if usage_stats:
        payload["usage_stats"] = usage_stats
    if error_message:
        payload["error_message"] = error_message

    headers = {
        "Content-Type": "application/json",
    }

    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    try:
        logger.info(f"[Webhook] Sending webhook to {FASTAPI_WEBHOOK_URL}")

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                FASTAPI_WEBHOOK_URL,
                json=payload,
                headers=headers
            )

        if response.status_code == 200:
            logger.info(f"[Webhook] Webhook sent successfully")
        else:
            logger.warning(f"[Webhook] Webhook returned {response.status_code}: {response.text}")

    except Exception as e:
        logger.error(f"[Webhook] Failed to send webhook: {e}")


# =============================================================================
# Queue Trigger - QuickBooks Ingestion Processing
# =============================================================================
@app.queue_trigger(
    arg_name="msg",
    queue_name="%QUICKBOOK_PROCESSING_QUEUE%",
    connection="AzureWebJobsStorage"
)
def process_quickbooks_queue(msg: func.QueueMessage):
    """
    Queue-triggered function for QuickBooks data ingestion.
    Processes raw connector data into insight chunks using the unified ChunkingService.
    """
    # Import connector models and chunking service only when needed
    from shared.database.models.connector import (
        ConnectorConfig, ConnectorRawData, ConnectorChunk, ConnectorType, SyncStatus
    )
    from shared.services.chunking import get_chunking_service, ChunkInput, SourceType

    message_body = msg.get_body().decode('utf-8')
    message_data = json.loads(message_body)

    connector_config_id = message_data.get("connector_config_id")
    entity_types = message_data.get("entity_types", [])
    tenant_id = message_data.get("tenant_id")
    company_id = message_data.get("company_id")
    retry_cycle = message_data.get("retry_cycle", 1)

    logger.info("=" * 70)
    logger.info(f"[ProcessQuickBooks] Starting ingestion from queue")
    logger.info(f"  Connector Config ID: {connector_config_id}")
    logger.info(f"  Entity Types: {entity_types}")
    logger.info(f"  Dequeue count: {msg.dequeue_count}")
    logger.info(f"  Retry cycle: {retry_cycle}/{MAX_RETRY_CYCLES}")
    logger.info("=" * 70)

    start_time = time.time()
    session = None

    try:
        session = get_db_session()

        # Step 1: Load connector config
        _send_quickbooks_progress_webhook(
            connector_config_id=connector_config_id,
            step=1,
            step_name="Loading Configuration",
            progress=5
        )

        from sqlmodel import select
        config = session.exec(
            select(ConnectorConfig).where(ConnectorConfig.id == connector_config_id)
        ).first()

        if not config:
            logger.error(f"[ProcessQuickBooks] Connector config not found: {connector_config_id}")
            return

        logger.info(f"[ProcessQuickBooks] Processing connector: {config.external_company_name}")

        # Step 2: Query raw data
        _send_quickbooks_progress_webhook(
            connector_config_id=connector_config_id,
            step=2,
            step_name="Querying Raw Data",
            progress=15
        )

        # If no entity types specified, process all unprocessed entities
        if not entity_types:
            # Get distinct unprocessed entity types
            raw_data_query = select(ConnectorRawData.entity_type).where(
                ConnectorRawData.connector_config_id == connector_config_id,
                ConnectorRawData.is_processed == False
            ).distinct()
            entity_types = [row for row in session.exec(raw_data_query).all()]
            logger.info(f"[ProcessQuickBooks] Found unprocessed entity types: {entity_types}")

        if not entity_types:
            logger.info(f"[ProcessQuickBooks] No unprocessed data to process")
            _send_quickbooks_progress_webhook(
                connector_config_id=connector_config_id,
                step=6,
                step_name="Completed",
                progress=100,
                status="completed"
            )
            return

        total_chunks_created = 0
        total_records_processed = 0
        entities_completed = []
        chunking_service = get_chunking_service()

        # Step 3: Process each entity type
        for entity_idx, entity_type in enumerate(entity_types):
            # Calculate progress: 20% to 80% for entity processing
            entity_progress = 20 + int((entity_idx / len(entity_types)) * 60)

            _send_quickbooks_progress_webhook(
                connector_config_id=connector_config_id,
                step=3,
                step_name=f"Processing {entity_type}",
                progress=entity_progress,
                current_entity=entity_type,
                entities_completed=entities_completed
            )

            logger.info(f"[ProcessQuickBooks] Processing entity type: {entity_type}")

            # Query raw data for this entity type
            raw_data_query = select(ConnectorRawData).where(
                ConnectorRawData.connector_config_id == connector_config_id,
                ConnectorRawData.entity_type == entity_type,
                ConnectorRawData.is_processed == False
            )
            raw_records = session.exec(raw_data_query).all()

            if not raw_records:
                logger.info(f"[ProcessQuickBooks] No unprocessed {entity_type} records")
                entities_completed.append(entity_type)
                continue

            logger.info(f"[ProcessQuickBooks] Found {len(raw_records)} unprocessed {entity_type} records")

            # Convert raw data to dict list for ChunkInput
            records_data = [r.raw_data for r in raw_records]
            raw_data_ids = [r.id for r in raw_records]

            # Create ChunkInput for this entity type
            chunk_input = ChunkInput(
                source_type=SourceType.CONNECTOR,
                tenant_id=tenant_id,
                company_id=company_id,
                connector_config_id=connector_config_id,
                connector_type="quickbooks",
                entity_type=entity_type,
                raw_records=records_data,
            )

            try:
                # Process through ChunkingService
                # Use run_async to safely handle concurrent queue processing
                result = run_async(chunking_service.process(chunk_input))

                logger.info(f"[ProcessQuickBooks] {entity_type}: Created {len(result.chunks)} chunks from {len(raw_records)} records")

                # Delete existing chunks for this entity type (idempotency)
                from sqlmodel import delete
                existing_chunks_stmt = delete(ConnectorChunk).where(
                    ConnectorChunk.connector_config_id == connector_config_id,
                    ConnectorChunk.entity_type == entity_type
                )
                session.exec(existing_chunks_stmt)
                session.commit()

                # Save new chunks
                for chunk_output in result.chunks:
                    connector_chunk = ConnectorChunk(
                        tenant_id=tenant_id,
                        company_id=company_id,
                        connector_config_id=connector_config_id,
                        connector_type=ConnectorType.QUICKBOOKS,
                        entity_type=entity_type,
                        entity_id=chunk_output.entity_id,
                        entity_name=chunk_output.entity_name,
                        content=chunk_output.content,
                        summary=chunk_output.summary,
                        pillar=chunk_output.pillar,
                        chunk_type=chunk_output.chunk_type or "aggregated_summary",
                        confidence_score=chunk_output.confidence_score,
                        metadata_json=chunk_output.metadata,
                        embedding=chunk_output.embedding,
                        data_as_of=chunk_output.data_as_of,
                    )
                    session.add(connector_chunk)

                # Mark raw data as processed
                for raw_record in raw_records:
                    raw_record.is_processed = True
                    raw_record.processed_at = datetime.utcnow()
                    session.add(raw_record)

                session.commit()

                total_chunks_created += len(result.chunks)
                total_records_processed += len(raw_records)
                entities_completed.append(entity_type)

            except Exception as entity_error:
                logger.error(f"[ProcessQuickBooks] Failed to process {entity_type}: {entity_error}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue with other entity types

        # Step 4: Update connector config
        _send_quickbooks_progress_webhook(
            connector_config_id=connector_config_id,
            step=5,
            step_name="Storing Results",
            progress=95,
            entities_completed=entities_completed
        )

        config.last_sync_at = datetime.utcnow()
        config.last_sync_status = SyncStatus.COMPLETED
        config.updated_at = datetime.utcnow()
        session.add(config)
        session.commit()

        total_time = time.time() - start_time

        logger.info("=" * 70)
        logger.info(f"[ProcessQuickBooks] INGESTION COMPLETED")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Entities processed: {len(entities_completed)}")
        logger.info(f"  Records processed: {total_records_processed}")
        logger.info(f"  Chunks created: {total_chunks_created}")
        logger.info("=" * 70)

        # Step 6: Send completion webhook
        _send_quickbooks_progress_webhook(
            connector_config_id=connector_config_id,
            step=6,
            step_name="Completed",
            progress=100,
            status="completed",
            entities_completed=entities_completed,
            records_processed=total_records_processed,
            chunks_created=total_chunks_created
        )

    except Exception as e:
        total_time = time.time() - start_time
        error_message = str(e)[:1000]

        logger.error(f"[ProcessQuickBooks] PROCESSING FAILED after {total_time:.2f}s")
        logger.error(f"  Error: {error_message}")

        import traceback
        logger.error(traceback.format_exc())

        if session:
            try:
                # Update connector config with error
                from sqlmodel import select
                config = session.exec(
                    select(ConnectorConfig).where(ConnectorConfig.id == connector_config_id)
                ).first()

                if config:
                    config.last_sync_status = SyncStatus.FAILED
                    config.last_sync_error = error_message
                    config.updated_at = datetime.utcnow()
                    session.add(config)
                    session.commit()

            except Exception as db_error:
                logger.error(f"[ProcessQuickBooks] Failed to update config status: {db_error}")

        _send_quickbooks_progress_webhook(
            connector_config_id=connector_config_id,
            step=6,
            step_name="Error",
            progress=0,
            status="failed",
            error_message=error_message
        )

        # Re-raise for queue retry
        raise

    finally:
        if session:
            session.close()


def _send_quickbooks_progress_webhook(
    connector_config_id: str,
    step: int,
    step_name: str,
    progress: int,
    status: str = "processing",
    current_entity: str = None,
    entities_completed: list = None,
    records_processed: int = None,
    chunks_created: int = None,
    error_message: str = None
):
    """Send progress webhook for QuickBooks ingestion."""
    if not QUICKBOOK_WEBHOOK_URL:
        return

    payload = {
        "connector_config_id": connector_config_id,
        "status": status,
        "step": step,
        "step_name": step_name,
        "progress": progress,
    }

    if current_entity:
        payload["current_entity"] = current_entity
    if entities_completed:
        payload["entities_completed"] = entities_completed
    if records_processed is not None:
        payload["records_processed"] = records_processed
    if chunks_created is not None:
        payload["chunks_created"] = chunks_created
    if error_message:
        payload["error_message"] = error_message

    headers = {
        "Content-Type": "application/json",
    }
    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(QUICKBOOK_WEBHOOK_URL, json=payload, headers=headers)
    except Exception as e:
        logger.warning(f"[QuickBooksWebhook] Progress webhook failed: {e}")


# =============================================================================
# Queue Trigger - Carbon Voice Ingestion Processing
# =============================================================================
@app.queue_trigger(
    arg_name="msg",
    queue_name="%CARBONVOICE_PROCESSING_QUEUE%",
    connection="AzureWebJobsStorage"
)
def process_carbonvoice_queue(msg: func.QueueMessage):
    """
    Queue-triggered function for Carbon Voice data ingestion.
    Processes raw connector data (workspaces, channels, messages, action items)
    into insight chunks using the unified ChunkingService.
    """
    # Import connector models and chunking service only when needed
    from shared.database.models.connector import (
        ConnectorConfig, ConnectorRawData, ConnectorChunk, ConnectorType, SyncStatus
    )
    from shared.services.chunking import get_chunking_service, ChunkInput, SourceType

    message_body = msg.get_body().decode('utf-8')
    message_data = json.loads(message_body)

    connector_config_id = message_data.get("connector_config_id")
    entity_types = message_data.get("entity_types", [])
    tenant_id = message_data.get("tenant_id")
    company_id = message_data.get("company_id")
    retry_cycle = message_data.get("retry_cycle", 1)

    logger.info("=" * 70)
    logger.info(f"[ProcessCarbonVoice] Starting ingestion from queue")
    logger.info(f"  Connector Config ID: {connector_config_id}")
    logger.info(f"  Entity Types: {entity_types}")
    logger.info(f"  Dequeue count: {msg.dequeue_count}")
    logger.info(f"  Retry cycle: {retry_cycle}/{MAX_RETRY_CYCLES}")
    logger.info("=" * 70)

    start_time = time.time()
    session = None

    try:
        session = get_db_session()

        # Step 1: Load connector config
        _send_carbonvoice_progress_webhook(
            connector_config_id=connector_config_id,
            step=1,
            step_name="Loading Configuration",
            progress=5
        )

        from sqlmodel import select
        config = session.exec(
            select(ConnectorConfig).where(ConnectorConfig.id == connector_config_id)
        ).first()

        if not config:
            logger.error(f"[ProcessCarbonVoice] Connector config not found: {connector_config_id}")
            return

        logger.info(f"[ProcessCarbonVoice] Processing connector: {config.external_company_name}")

        # Step 2: Query raw data
        _send_carbonvoice_progress_webhook(
            connector_config_id=connector_config_id,
            step=2,
            step_name="Querying Raw Data",
            progress=15
        )

        # If no entity types specified, process all unprocessed entities
        if not entity_types:
            # Get distinct unprocessed entity types
            raw_data_query = select(ConnectorRawData.entity_type).where(
                ConnectorRawData.connector_config_id == connector_config_id,
                ConnectorRawData.is_processed == False
            ).distinct()
            entity_types = [row for row in session.exec(raw_data_query).all()]
            logger.info(f"[ProcessCarbonVoice] Found unprocessed entity types: {entity_types}")

        if not entity_types:
            logger.info(f"[ProcessCarbonVoice] No unprocessed data to process")
            _send_carbonvoice_progress_webhook(
                connector_config_id=connector_config_id,
                step=6,
                step_name="Completed",
                progress=100,
                status="completed"
            )
            return

        total_chunks_created = 0
        total_records_processed = 0
        entities_completed = []
        chunking_service = get_chunking_service()

        # Step 3: Process each entity type
        for entity_idx, entity_type in enumerate(entity_types):
            # Calculate progress: 20% to 80% for entity processing
            entity_progress = 20 + int((entity_idx / len(entity_types)) * 60)

            _send_carbonvoice_progress_webhook(
                connector_config_id=connector_config_id,
                step=3,
                step_name=f"Processing {entity_type}",
                progress=entity_progress,
                current_entity=entity_type,
                entities_completed=entities_completed
            )

            logger.info(f"[ProcessCarbonVoice] Processing entity type: {entity_type}")

            # Query raw data for this entity type
            raw_data_query = select(ConnectorRawData).where(
                ConnectorRawData.connector_config_id == connector_config_id,
                ConnectorRawData.entity_type == entity_type,
                ConnectorRawData.is_processed == False
            )
            raw_records = session.exec(raw_data_query).all()

            if not raw_records:
                logger.info(f"[ProcessCarbonVoice] No unprocessed {entity_type} records")
                entities_completed.append(entity_type)
                continue

            logger.info(f"[ProcessCarbonVoice] Found {len(raw_records)} unprocessed {entity_type} records")

            # Convert raw data to dict list for ChunkInput
            records_data = [r.raw_data for r in raw_records]
            raw_data_ids = [r.id for r in raw_records]

            # Create ChunkInput for this entity type
            chunk_input = ChunkInput(
                source_type=SourceType.CONNECTOR,
                tenant_id=tenant_id,
                company_id=company_id,
                connector_config_id=connector_config_id,
                connector_type="carbonvoice",
                entity_type=entity_type,
                raw_records=records_data,
            )

            try:
                # Process through ChunkingService
                # Use run_async to safely handle concurrent queue processing
                result = run_async(chunking_service.process(chunk_input))

                logger.info(f"[ProcessCarbonVoice] {entity_type}: Created {len(result.chunks)} chunks from {len(raw_records)} records")

                # Delete existing chunks for this entity type (idempotency)
                from sqlmodel import delete
                existing_chunks_stmt = delete(ConnectorChunk).where(
                    ConnectorChunk.connector_config_id == connector_config_id,
                    ConnectorChunk.entity_type == entity_type
                )
                session.exec(existing_chunks_stmt)
                session.commit()

                # Save new chunks
                for chunk_output in result.chunks:
                    connector_chunk = ConnectorChunk(
                        tenant_id=tenant_id,
                        company_id=company_id,
                        connector_config_id=connector_config_id,
                        connector_type=ConnectorType.CARBONVOICE,
                        entity_type=entity_type,
                        entity_id=chunk_output.entity_id,
                        entity_name=chunk_output.entity_name,
                        content=chunk_output.content,
                        summary=chunk_output.summary,
                        pillar=chunk_output.pillar,
                        chunk_type=chunk_output.chunk_type or "aggregated_summary",
                        confidence_score=chunk_output.confidence_score,
                        metadata_json=chunk_output.metadata,
                        embedding=chunk_output.embedding,
                        data_as_of=chunk_output.data_as_of,
                    )
                    session.add(connector_chunk)

                # Mark raw data as processed
                for raw_record in raw_records:
                    raw_record.is_processed = True
                    raw_record.processed_at = datetime.utcnow()
                    session.add(raw_record)

                session.commit()

                total_chunks_created += len(result.chunks)
                total_records_processed += len(raw_records)
                entities_completed.append(entity_type)

            except Exception as entity_error:
                logger.error(f"[ProcessCarbonVoice] Failed to process {entity_type}: {entity_error}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue with other entity types

        # Step 4: Update connector config
        _send_carbonvoice_progress_webhook(
            connector_config_id=connector_config_id,
            step=5,
            step_name="Storing Results",
            progress=95,
            entities_completed=entities_completed
        )

        config.last_sync_at = datetime.utcnow()
        config.last_sync_status = SyncStatus.COMPLETED
        config.updated_at = datetime.utcnow()
        session.add(config)
        session.commit()

        total_time = time.time() - start_time

        logger.info("=" * 70)
        logger.info(f"[ProcessCarbonVoice] INGESTION COMPLETED")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Entities processed: {len(entities_completed)}")
        logger.info(f"  Records processed: {total_records_processed}")
        logger.info(f"  Chunks created: {total_chunks_created}")
        logger.info("=" * 70)

        # Step 6: Send completion webhook
        _send_carbonvoice_progress_webhook(
            connector_config_id=connector_config_id,
            step=6,
            step_name="Completed",
            progress=100,
            status="completed",
            entities_completed=entities_completed,
            records_processed=total_records_processed,
            chunks_created=total_chunks_created
        )

    except Exception as e:
        total_time = time.time() - start_time
        error_message = str(e)[:1000]

        logger.error(f"[ProcessCarbonVoice] PROCESSING FAILED after {total_time:.2f}s")
        logger.error(f"  Error: {error_message}")

        import traceback
        logger.error(traceback.format_exc())

        if session:
            try:
                # Update connector config with error
                from sqlmodel import select
                config = session.exec(
                    select(ConnectorConfig).where(ConnectorConfig.id == connector_config_id)
                ).first()

                if config:
                    config.last_sync_status = SyncStatus.FAILED
                    config.last_sync_error = error_message
                    config.updated_at = datetime.utcnow()
                    session.add(config)
                    session.commit()

            except Exception as db_error:
                logger.error(f"[ProcessCarbonVoice] Failed to update config status: {db_error}")

        _send_carbonvoice_progress_webhook(
            connector_config_id=connector_config_id,
            step=6,
            step_name="Error",
            progress=0,
            status="failed",
            error_message=error_message
        )

        # Re-raise for queue retry
        raise

    finally:
        if session:
            session.close()


def _send_carbonvoice_progress_webhook(
    connector_config_id: str,
    step: int,
    step_name: str,
    progress: int,
    status: str = "processing",
    current_entity: str = None,
    entities_completed: list = None,
    records_processed: int = None,
    chunks_created: int = None,
    error_message: str = None
):
    """Send progress webhook for Carbon Voice ingestion."""
    if not CARBONVOICE_WEBHOOK_URL:
        return

    payload = {
        "connector_config_id": connector_config_id,
        "status": status,
        "step": step,
        "step_name": step_name,
        "progress": progress,
    }

    if current_entity:
        payload["current_entity"] = current_entity
    if entities_completed:
        payload["entities_completed"] = entities_completed
    if records_processed is not None:
        payload["records_processed"] = records_processed
    if chunks_created is not None:
        payload["chunks_created"] = chunks_created
    if error_message:
        payload["error_message"] = error_message

    headers = {
        "Content-Type": "application/json",
    }
    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(CARBONVOICE_WEBHOOK_URL, json=payload, headers=headers)
    except Exception as e:
        logger.warning(f"[CarbonVoiceWebhook] Progress webhook failed: {e}")
