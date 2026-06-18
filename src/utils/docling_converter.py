"""
Docling conversion helper: convert PDFs and other documents to Markdown with OCR.

This module provides a minimal wrapper around Docling's DocumentConverter.
It is defensive: if `docling` is not installed, it raises an informative ImportError.
"""

import os
from typing import List, Dict, Optional
import logging
import re


def convert_to_markdown(
    input_path: str, ocr_engine: str = "easyocr", do_ocr: bool = True
) -> str:
    """
    Convert a document (PDF, DOCX, HTML, etc.) to a Markdown string using Docling.

    Args:
        input_path: Path to the input file.
        ocr_engine: Preferred OCR engine name (e.g., 'easyocr', 'tesserocr').
        do_ocr: Whether to run OCR on scanned PDFs.

    Returns:
        Markdown string containing the converted document.

    Raises:
        ImportError: If docling is not installed.
        Exception: If conversion fails for other reasons.
    """
    logger = logging.getLogger("uvicorn.error")

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except Exception as e:  # pragma: no cover - environment dependent
        raise ImportError(
            "Docling is not installed or cannot be imported. Install it via `uv add docling` or `pip install docling`"
        ) from e

    try:
        # Force OCR engines to run on CPU only.
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = bool(do_ocr)

        # Force EasyOCR / Docling OCR to use CPU even when CUDA is available.
        try:
            if hasattr(pipeline_options, "ocr_options"):
                pipeline_options.ocr_options.use_gpu = False
        except Exception:
            pass

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        # The convert API may vary between docling versions. We try common call patterns.
        converted = None
        if hasattr(doc_converter, "convert"):
            converted = doc_converter.convert(input_path)
        elif hasattr(doc_converter, "from_path"):
            converted = doc_converter.from_path(input_path)
        else:
            # Last resort: try calling as a callable
            converted = doc_converter(input_path)

        if isinstance(converted, str):
            return converted

        # Modern Docling 2.0+ returns a ConversionResult object
        if hasattr(converted, "document") and hasattr(converted.document, "export_to_markdown"):
            return converted.document.export_to_markdown()

        # If converted is iterable (older versions), concatenate text/markdown fields
        parts = []
        try:
            for item in converted or []:
                # common datamodel attributes
                text = None
                if hasattr(item, "markdown"):
                    text = getattr(item, "markdown")
                elif hasattr(item, "text"):
                    text = getattr(item, "text")
                elif hasattr(item, "content"):
                    text = getattr(item, "content")

                if text:
                    parts.append(str(text))

            if parts:
                return "\n\n".join(parts)
        except Exception:
            logger.exception("Failed to extract converted text from docling output")

        # If all else fails, stringify the object
        return str(converted)
    except Exception as e:  # pragma: no cover - runtime dependent
        logger.error(f"Docling conversion failed: {e}")
        raise


def extract_markdown_chapters(markdown_text: str) -> List[Dict[str, int]]:
    """
    Extract chapter boundaries from a Markdown string based on heading lines.

    Args:
        markdown_text: The Markdown string to scan.

    Returns:
        List of chapter objects with title, start_offset, and end_offset.
    """
    if not markdown_text:
        return []

    chapters: List[Dict[str, int]] = []
    heading_re = re.compile(r"^(#{1,2})\s+(.*)$")
    current_start = 0
    offset = 0
    last_chapter = None

    for line in markdown_text.splitlines(keepends=True):
        stripped = line.strip()
        match = heading_re.match(stripped)
        if match:
            title = match.group(2).strip()
            if not title:
                offset += len(line)
                continue
                
            if last_chapter is not None:
                last_chapter["end_offset"] = offset
            last_chapter = {
                "title": title,
                "start_offset": offset,
                "end_offset": len(markdown_text),
            }
            chapters.append(last_chapter)

        offset += len(line)

    if chapters and chapters[-1].get("end_offset") is None:
        chapters[-1]["end_offset"] = len(markdown_text)

    if not chapters:
        chapters = [
            {
                "title": "Document",
                "start_offset": 0,
                "end_offset": len(markdown_text),
            }
        ]

    return chapters
