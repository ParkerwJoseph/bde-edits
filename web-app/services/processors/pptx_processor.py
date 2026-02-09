import io
import os
import base64
import time
import subprocess
import tempfile
from typing import List, Tuple

from PIL import Image
from pdf2image import convert_from_path

from utils.logger import get_logger

logger = get_logger(__name__)


class PPTXProcessor:
    """
    Processes PPTX documents by converting slides to images for vision-based LLM analysis.
    Converts PPTX → PDF → Images (one per slide).
    """

    def __init__(self, dpi: int = 150, max_image_size: Tuple[int, int] = (1536, 1536)):
        self.dpi = dpi
        self.max_image_size = max_image_size
        logger.info(f"[PPTXProcessor] Initialized with DPI={dpi}, max_size={max_image_size}")

    def process(self, file_path: str) -> List[dict]:
        """
        Convert PPTX slides to base64 images.

        Args:
            file_path: Path to the PPTX file

        Returns:
            List of slide dicts with 'page_number', 'content_type', 'image_base64', etc.
        """
        logger.info(f"[PPTXProcessor] Converting PPTX to images (DPI={self.dpi})...")
        start_time = time.time()

        # Convert PPTX to PDF first
        pdf_path = self._convert_to_pdf(file_path)

        if not pdf_path:
            raise ValueError("Failed to convert PPTX to PDF. Ensure LibreOffice is installed.")

        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=self.dpi, fmt='PNG')
            logger.info(f"[PPTXProcessor] Converted {len(images)} slides")

            slides = []
            for slide_num, image in enumerate(images, start=1):
                image = self._resize_image(image)
                base64_image = self._image_to_base64(image)

                slides.append({
                    "page_number": slide_num,
                    "content_type": "image",
                    "image_base64": base64_image,
                    "width": image.width,
                    "height": image.height
                })

                logger.info(f"  Slide {slide_num}: {image.width}x{image.height}, {len(base64_image)/1024:.1f}KB")

        finally:
            # Clean up temp PDF
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)

        elapsed = time.time() - start_time
        logger.info(f"[PPTXProcessor] Done in {elapsed:.2f}s - {len(slides)} slides")

        return slides

    def _convert_to_pdf(self, pptx_path: str) -> str:
        """
        Convert PPTX to PDF using LibreOffice.

        Args:
            pptx_path: Path to the PPTX file

        Returns:
            Path to the generated PDF file
        """
        logger.info("[PPTXProcessor] Converting PPTX to PDF via LibreOffice...")

        # Create temp directory for output
        temp_dir = tempfile.mkdtemp()

        try:
            # Run LibreOffice conversion
            result = subprocess.run([
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", temp_dir,
                pptx_path
            ], capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"[PPTXProcessor] LibreOffice error: {result.stderr}")
                raise ValueError(f"LibreOffice conversion failed: {result.stderr}")

            # Find the generated PDF
            pdf_files = [f for f in os.listdir(temp_dir) if f.endswith('.pdf')]
            if not pdf_files:
                raise ValueError("No PDF file generated")

            pdf_path = os.path.join(temp_dir, pdf_files[0])
            logger.info(f"[PPTXProcessor] PDF generated: {pdf_path}")

            return pdf_path

        except FileNotFoundError:
            raise ValueError("LibreOffice (soffice) not found. Please install LibreOffice.")
        except subprocess.TimeoutExpired:
            raise ValueError("LibreOffice conversion timed out")

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds max dimensions."""
        if image.width <= self.max_image_size[0] and image.height <= self.max_image_size[1]:
            return image

        ratio = min(
            self.max_image_size[0] / image.width,
            self.max_image_size[1] / image.height
        )
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
