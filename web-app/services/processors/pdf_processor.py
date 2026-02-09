import gc
import io
import base64
import time
from typing import List, Tuple, Optional

from PIL import Image
from pdf2image import convert_from_path, pdfinfo_from_path

from utils.logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """
    Processes PDF documents by converting pages to images for vision-based LLM analysis.
    Also extracts structured table data using pdfplumber for financial/tabular pages.
    Each page is converted to a base64-encoded image, and tables are extracted as structured text.
    Processes one page at a time to minimize memory usage.
    """

    def __init__(self, dpi: int = 150, max_image_size: Tuple[int, int] = (1536, 1536)):
        self.dpi = dpi
        self.max_image_size = max_image_size
        logger.info(f"[PDFProcessor] Initialized with DPI={dpi}, max_size={max_image_size}")

    def process(self, file_path: str) -> List[dict]:
        """
        Convert PDF pages to base64 images one page at a time.
        Also extracts structured table data from pages that contain tables.

        Args:
            file_path: Path to the PDF file

        Returns:
            List of page dicts with 'page_number', 'content_type', 'image_base64',
            and optionally 'table_data' for pages with detected tables.
        """
        logger.info(f"[PDFProcessor] Converting PDF to images (DPI={self.dpi})...")
        start_time = time.time()

        # Get total page count first
        try:
            pdf_info = pdfinfo_from_path(file_path)
            total_pages = pdf_info.get("Pages", 0)
        except Exception:
            # Fallback: convert all at once to get count
            images = convert_from_path(file_path, dpi=self.dpi, fmt='PNG', first_page=1, last_page=1)
            total_pages = len(convert_from_path(file_path, dpi=10))  # Low DPI just for counting
            del images
            gc.collect()

        logger.info(f"[PDFProcessor] PDF has {total_pages} pages, processing one at a time...")

        # Extract tables from all pages using pdfplumber
        page_tables = self._extract_tables(file_path, total_pages)

        pages = []
        for page_num in range(1, total_pages + 1):
            # Convert single page to image
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

                page_dict = {
                    "page_number": page_num,
                    "content_type": "image",
                    "image_base64": base64_image,
                    "width": image.width,
                    "height": image.height
                }

                # Attach structured table data if tables were found on this page
                tables_for_page = page_tables.get(page_num)
                if tables_for_page:
                    page_dict["table_data"] = tables_for_page
                    logger.info(
                        f"  Page {page_num}/{total_pages}: {image.width}x{image.height}, "
                        f"{len(base64_image)/1024:.1f}KB, {len(tables_for_page)} table(s) extracted"
                    )
                else:
                    logger.info(f"  Page {page_num}/{total_pages}: {image.width}x{image.height}, {len(base64_image)/1024:.1f}KB")

                pages.append(page_dict)

                # Free memory immediately
                del image
                del images
                gc.collect()

        elapsed = time.time() - start_time
        tables_found = sum(1 for p in pages if p.get("table_data"))
        logger.info(f"[PDFProcessor] Done in {elapsed:.2f}s - {len(pages)} pages, {tables_found} pages with tables")

        return pages

    def _extract_tables(self, file_path: str, total_pages: int) -> dict:
        """
        Extract structured table data from all PDF pages using pdfplumber.

        Returns:
            Dict mapping page_number -> list of formatted table strings.
            Only includes pages that have meaningful tables.
        """
        page_tables = {}

        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    tables = page.extract_tables()

                    if not tables:
                        continue

                    formatted_tables = []
                    for table_idx, table in enumerate(tables):
                        formatted = self._format_table(table)
                        if formatted:
                            formatted_tables.append(formatted)

                    if formatted_tables:
                        page_tables[page_num] = formatted_tables
                        logger.debug(
                            f"[PDFProcessor] Page {page_num}: extracted {len(formatted_tables)} table(s)"
                        )

        except ImportError:
            logger.warning("[PDFProcessor] pdfplumber not installed, skipping table extraction")
        except Exception as e:
            logger.warning(f"[PDFProcessor] Table extraction failed (falling back to vision-only): {e}")

        return page_tables

    def _format_table(self, table: List[List[Optional[str]]]) -> Optional[str]:
        """
        Format a raw pdfplumber table into a clean markdown-style table string.

        Args:
            table: 2D list of cell values from pdfplumber

        Returns:
            Formatted table string, or None if the table is empty/trivial
        """
        if not table or len(table) < 2:
            return None

        # Clean cells: replace None with empty string, strip whitespace
        cleaned = []
        for row in table:
            cleaned_row = [(cell or "").strip() for cell in row]
            # Skip completely empty rows
            if any(cell for cell in cleaned_row):
                cleaned.append(cleaned_row)

        if len(cleaned) < 2:
            return None

        # Normalize column count (pad shorter rows)
        max_cols = max(len(row) for row in cleaned)
        for row in cleaned:
            while len(row) < max_cols:
                row.append("")

        # Calculate column widths for alignment
        col_widths = []
        for col_idx in range(max_cols):
            max_width = max(len(row[col_idx]) for row in cleaned)
            col_widths.append(max(max_width, 3))  # minimum width of 3

        # Build markdown table
        lines = []

        # Header row
        header = cleaned[0]
        header_line = "| " + " | ".join(
            cell.ljust(col_widths[i]) for i, cell in enumerate(header)
        ) + " |"
        lines.append(header_line)

        # Separator
        separator = "| " + " | ".join(
            "-" * col_widths[i] for i in range(max_cols)
        ) + " |"
        lines.append(separator)

        # Data rows
        for row in cleaned[1:]:
            data_line = "| " + " | ".join(
                cell.ljust(col_widths[i]) for i, cell in enumerate(row)
            ) + " |"
            lines.append(data_line)

        return "\n".join(lines)

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
