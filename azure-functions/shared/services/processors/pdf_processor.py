import gc
import io
import base64
import time
from typing import List, Tuple

from PIL import Image
from pdf2image import convert_from_path, pdfinfo_from_path

from shared.utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """
    Processes PDF documents by converting pages to images for vision-based LLM analysis.
    """

    def __init__(self, dpi: int = 150, max_image_size: Tuple[int, int] = (1536, 1536)):
        self.dpi = dpi
        self.max_image_size = max_image_size
        logger.info(f"[PDFProcessor] Initialized with DPI={dpi}, max_size={max_image_size}")

    def process(self, file_path: str) -> List[dict]:
        logger.info(f"[PDFProcessor] Converting PDF to images (DPI={self.dpi})...")
        start_time = time.time()

        try:
            pdf_info = pdfinfo_from_path(file_path)
            total_pages = pdf_info.get("Pages", 0)
        except Exception:
            images = convert_from_path(file_path, dpi=self.dpi, fmt='PNG', first_page=1, last_page=1)
            total_pages = len(convert_from_path(file_path, dpi=10))
            del images
            gc.collect()

        logger.info(f"[PDFProcessor] PDF has {total_pages} pages, processing one at a time...")

        pages = []
        for page_num in range(1, total_pages + 1):
            images = convert_from_path(
                file_path,
                dpi=self.dpi,
                fmt='PNG',
                first_page=page_num,
                last_page=page_num
            )

            if images:
                image = images[0]
                image = self._resize_image(image)
                base64_image = self._image_to_base64(image)

                pages.append({
                    "page_number": page_num,
                    "content_type": "image",
                    "image_base64": base64_image,
                    "width": image.width,
                    "height": image.height
                })

                logger.info(f"  Page {page_num}/{total_pages}: {image.width}x{image.height}")

                del image
                del images
                gc.collect()

        elapsed = time.time() - start_time
        logger.info(f"[PDFProcessor] Done in {elapsed:.2f}s - {len(pages)} pages")

        return pages

    def _resize_image(self, image: Image.Image) -> Image.Image:
        if image.width <= self.max_image_size[0] and image.height <= self.max_image_size[1]:
            return image

        ratio = min(
            self.max_image_size[0] / image.width,
            self.max_image_size[1] / image.height
        )
        new_size = (int(image.width * ratio), int(image.height * ratio))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _image_to_base64(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
