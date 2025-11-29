import io
import mimetypes
from typing import List, Tuple
from pdf2image import convert_from_bytes
from PIL import Image

async def prepare_pages(document_url: str):
    """
    For URL inputs, we pass the URL directly to Gemini.
    This avoids downloading/processing PDFs when using URLs.
    """
    # Return in same structure: (page_no, data)
    return [("1", document_url)]


def process_uploaded_file(file_bytes: bytes, mime: str) -> List[Tuple[str, Tuple[bytes, str]]]:
    """
    Process uploaded file (PDF or image) and return all pages.
    
    Args:
        file_bytes: File content as bytes
        mime: MIME type of the file
    
    Returns:
        List of (page_no, (image_bytes, mime)) tuples
    """
    pages = []
    
    if "pdf" in mime.lower():
        # Convert PDF to images - all pages
        try:
            pdf_images = convert_from_bytes(file_bytes, dpi=200)
            
            for idx, img in enumerate(pdf_images, start=1):
                # Convert PIL Image to bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                pages.append((str(idx), (img_bytes.getvalue(), "image/png")))
        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    elif "image" in mime.lower():
        # Single image file
        pages.append(("1", (file_bytes, mime)))
    
    else:
        raise ValueError(f"Unsupported file type: {mime}. Please provide PDF or image file.")
    
    return pages
