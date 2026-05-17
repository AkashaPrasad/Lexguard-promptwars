"""Document parsing utilities for PDF, DOCX, and image files."""
import asyncio
import io
from typing import Optional

import fitz  # PyMuPDF
from docx import Document

from config import (
    DOCUMENT_AI_PROCESSOR_ID,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    MAX_CONTRACT_TEXT_BYTES,
)


def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    text_parts = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_image_with_document_ai(file_bytes: bytes, mime_type: str) -> str:
    """Use Google Document AI for OCR on image files."""
    try:
        from google.cloud import documentai

        client = documentai.DocumentProcessorServiceClient()
        name = client.processor_path(
            GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, DOCUMENT_AI_PROCESSOR_ID
        )
        raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        return result.document.text
    except Exception:
        return ""


def sanitize_text(text: str) -> str:
    """Remove null bytes and truncate to max size."""
    text = text.replace("\x00", "")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_CONTRACT_TEXT_BYTES:
        encoded = encoded[:MAX_CONTRACT_TEXT_BYTES]
        text = encoded.decode("utf-8", errors="ignore")
    return text


async def parse_document(file_bytes: bytes, mime_type: str, filename: str) -> str:
    """Parse a document file and return extracted text.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        mime_type: MIME type of the file.
        filename: Original filename (used for logging).

    Returns:
        Extracted plain text from the document.
    """
    loop = asyncio.get_event_loop()

    if mime_type == "application/pdf":
        text = await loop.run_in_executor(None, parse_pdf, file_bytes)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        text = await loop.run_in_executor(None, parse_docx, file_bytes)
    elif mime_type in ("image/png", "image/jpeg"):
        text = await loop.run_in_executor(
            None, parse_image_with_document_ai, file_bytes, mime_type
        )
    else:
        text = ""

    return sanitize_text(text)
