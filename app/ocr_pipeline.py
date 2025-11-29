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
    print(f"[URL PROCESSING] Preparing URL input for processing")
    print(f"[URL PROCESSING] URL: {document_url[:200]}{'...' if len(document_url) > 200 else ''}")
    # Return in same structure: (page_no, data)
    # Note: For URLs, we let Gemini handle multi-page PDFs
    print(f"[URL PROCESSING] URL prepared - Gemini will handle PDF pages automatically")
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
    
    print(f"[FILE PROCESSING] Processing file with MIME type: {mime}")
    
    if "pdf" in mime.lower():
        # Convert PDF to images - all pages
        print(f"[PDF PROCESSING] Converting PDF to images (DPI: 200)...")
        try:
            pdf_images = convert_from_bytes(file_bytes, dpi=200)
            print(f"[PDF PROCESSING] PDF converted successfully - found {len(pdf_images)} page(s)")
            
            for idx, img in enumerate(pdf_images, start=1):
                # Convert PIL Image to bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_size = len(img_bytes.getvalue())
                pages.append((str(idx), (img_bytes.getvalue(), "image/png")))
                print(f"[PDF PROCESSING] Page {idx} converted to PNG ({img_size / 1024:.2f} KB)")
        except Exception as e:
            print(f"[ERROR] Failed to process PDF: {str(e)}")
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    elif "image" in mime.lower():
        # Single image file
        print(f"[IMAGE PROCESSING] Processing single image file")
        img_size = len(file_bytes) / 1024
        print(f"[IMAGE PROCESSING] Image size: {img_size:.2f} KB")
        pages.append(("1", (file_bytes, mime)))
        print(f"[IMAGE PROCESSING] Image prepared for processing")
    
    else:
        print(f"[ERROR] Unsupported file type: {mime}")
        raise ValueError(f"Unsupported file type: {mime}. Please provide PDF or image file.")
    
    print(f"[FILE PROCESSING] File processing complete - {len(pages)} page(s) ready")
    return pages
