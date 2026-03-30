"""Path safety and upload validation utilities."""
import os
import uuid

from fastapi import HTTPException, UploadFile

MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


def safe_filename(original_filename: str) -> str:
    """Strip directory components and prefix with a short UUID to avoid collisions."""
    basename = os.path.basename(original_filename)
    stem, ext = os.path.splitext(basename)
    return f"{uuid.uuid4().hex[:12]}_{stem}{ext}"


async def validate_pdf_upload(file: UploadFile) -> None:
    """Validate that an upload is a real PDF under the size limit."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read first chunk to check magic bytes and measure size
    contents = await file.read()

    if len(contents) > MAX_PDF_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB size limit")

    if not contents[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    # Reset file position for downstream consumers
    await file.seek(0)
