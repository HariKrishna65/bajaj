import io
from typing import List, Tuple, Union
from pathlib import Path
import httpx
from PIL import Image
from pdf2image import convert_from_bytes
import mimetypes


async def download_document(url: str) -> Tuple[bytes, str]:
    """Download document from URL"""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        # If content type is not available, try to detect from URL
        if not content_type or content_type == "application/octet-stream":
            content_type = mimetypes.guess_type(url)[0] or "application/octet-stream"
        return resp.content, content_type.lower()


def read_local_file(file_path: Union[str, Path]) -> Tuple[bytes, str]:
    """Read local file (PDF or image) and return content and MIME type"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        # Fallback detection based on extension
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext in [".gif", ".bmp", ".tiff", ".webp"]:
            mime_type = f"image/{ext[1:]}"
        else:
            raise ValueError(f"Cannot determine MIME type for file: {file_path}")
    
    return content, mime_type.lower()


async def get_document_content(source: Union[str, bytes, Path]) -> Tuple[bytes, str]:
    """
    Unified function to get document content from various sources:
    - URL string (http/https) -> downloads from URL
    - File path string/Path -> reads local file
    - bytes -> returns as-is (assumes PDF)
    
    Returns: (content_bytes, mime_type)
    """
    # If it's bytes, assume PDF
    if isinstance(source, bytes):
        return source, "application/pdf"
    
    source_str = str(source)
    
    # Check if it's a URL
    if source_str.startswith(("http://", "https://")):
        return await download_document(source_str)
    
    # Otherwise, treat as local file path
    return read_local_file(source_str)


def pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """Convert PDF bytes to list of PIL Images using pdf2image"""
    return convert_from_bytes(pdf_bytes, dpi=200)


def read_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def prepare_pages(content: bytes, mime: str) -> List[Tuple[int, bytes, str]]:
    """
    Converts input to list of (page_no, image_bytes, mime)
    """
    pages = []

    if "pdf" in mime:
        images = pdf_to_images(content)
        for idx, img in enumerate(images, start=1):
            output = io.BytesIO()
            img.save(output, format="PNG")
            pages.append((idx, output.getvalue(), "image/png"))

    elif "image" in mime:
        img = read_image(content)
        output = io.BytesIO()
        img.save(output, format="PNG")
        pages.append((1, output.getvalue(), "image/png"))

    else:
        raise ValueError(f"Unsupported file type: {mime}")

    return pages

