import os
import time
from pathlib import Path
from typing import List
import uuid

from shared.config.settings import UPLOAD_DIR
from shared.utils.logger import get_logger
from shared.services.processors import PDFProcessor, DOCXProcessor, XLSXProcessor, PPTXProcessor, AudioProcessor

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Main document processor that delegates to specialized processors.
    """

    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        self.pdf_processor = PDFProcessor()
        self.pptx_processor = PPTXProcessor()
        self.docx_processor = DOCXProcessor()
        self.xlsx_processor = XLSXProcessor()
        self.audio_processor = AudioProcessor()
        logger.info("[DocumentProcessor] Initialized with all processors")

    def process_document(self, file_path: str, file_type: str) -> List[dict]:
        """
        Process a document and return list of pages/sections.
        """
        logger.info("=" * 60)
        logger.info(f"[DocumentProcessor] Processing: {file_path}")
        logger.info(f"  Type: {file_type}, Size: {os.path.getsize(file_path) / 1024:.1f} KB")

        start_time = time.time()

        if file_type == "pdf":
            pages = self.pdf_processor.process(file_path)
        elif file_type == "pptx":
            pages = self.pptx_processor.process(file_path)
        elif file_type == "docx":
            pages = self.docx_processor.process(file_path)
        elif file_type == "xlsx":
            pages = self.xlsx_processor.process(file_path)
        elif file_type == "audio":
            pages = self.audio_processor.process(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        elapsed = time.time() - start_time
        logger.info(f"[DocumentProcessor] Done in {elapsed:.2f}s - {len(pages)} pages/sections")
        logger.info("=" * 60)

        return pages

    def save_uploaded_file(self, file_content: bytes, filename: str, tenant_id: str) -> str:
        """Save uploaded file to disk and return the path."""
        tenant_dir = os.path.join(UPLOAD_DIR, tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)

        ext = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(tenant_dir, unique_filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"[DocumentProcessor] Saved: {file_path} ({len(file_content)/1024:.1f} KB)")
        return file_path
