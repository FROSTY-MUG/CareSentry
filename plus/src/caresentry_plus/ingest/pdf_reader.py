"""Offline Clinical Document and PDF Ingestion (F-15).

Extracts text and tabular clinical data from offline PDF medical records
to directly feed the StructuredExtractor (F-04).
Provides explicit fail-safe error handling for unreadable or scanned documents.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("caresentry_plus.ingest")


class IngestionError(Exception):
    """Base exception for document ingestion failures."""
    pass


class UnreadableScannedDocumentError(IngestionError):
    """Raised when a PDF contains pure raster images with no extractable text."""
    pass


class PDFRecordIngestion:
    """Offline PDF document parser with clear error handling for unreadable scans."""

    def __init__(self):
        self._pypdf_available = False
        try:
            import pypdf
            self._pypdf_available = True
        except ImportError:
            pass

    def extract_text(self, file_path: Path) -> str:
        """Extract text from PDF file without network dependencies.
        
        Raises UnreadableScannedDocumentError if document cannot be parsed into text.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extracted_pages = []

        if self._pypdf_available:
            import pypdf
            try:
                reader = pypdf.PdfReader(str(file_path))
                for page_idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t and t.strip():
                        extracted_pages.append(t.strip())
            except Exception as e:
                raise IngestionError(f"Corrupt or unreadable PDF document ({e})") from e
        else:
            # Fallback naive binary stream text extraction for offline environments without pypdf
            try:
                content = file_path.read_bytes()
                # Search for Text stream blocks Between BT and ET markers
                text_matches = re.findall(rb"\((.*?)\)\s*Tj", content)
                if text_matches:
                    decoded = [m.decode("latin1", errors="ignore") for m in text_matches]
                    extracted_pages.append(" ".join(decoded))
            except Exception as e:
                raise IngestionError(f"Failed to read PDF binary stream ({e})") from e

        combined_text = "\n\n".join(extracted_pages).strip()

        # Fail clearly if document yields zero text (scanned image or corrupted raster)
        if not combined_text or len(combined_text) < 15:
            raise UnreadableScannedDocumentError(
                f"Document '{file_path.name}' contains scanned raster images without embedded OCR text. "
                "Offline extraction requires OCR pre-processing or digitized text records."
            )

        return combined_text
