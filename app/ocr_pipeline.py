import io
import mimetypes
import httpx
from typing import List, Tuple
from pdf2image import convert_from_bytes
from PIL import Image

async def download_document(url: str) -> Tuple[bytes, str]:
    """
    Download document from URL and return (file_bytes, mime_type).
    """
    print(f"[URL DOWNLOAD] Downloading document from URL...")
    print(f"[URL DOWNLOAD] URL: {url[:200]}{'...' if len(url) > 200 else ''}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            file_bytes = response.content
            file_size_mb = len(file_bytes) / (1024 * 1024)
            print(f"[URL DOWNLOAD] Downloaded successfully - {file_size_mb:.2f} MB ({len(file_bytes)} bytes)")
            
            # Detect MIME type from Content-Type header or URL
            mime = response.headers.get("content-type", "").split(";")[0].strip()
            if not mime or mime == "application/octet-stream":
                # Try to detect from URL extension
                detected_mime, _ = mimetypes.guess_type(url)
                if detected_mime:
                    mime = detected_mime
                    print(f"[URL DOWNLOAD] Detected MIME type from URL: {mime}")
                else:
                    # Default based on content
                    if file_bytes.startswith(b'%PDF'):
                        mime = "application/pdf"
                    elif file_bytes.startswith(b'\x89PNG'):
                        mime = "image/png"
                    elif file_bytes.startswith(b'\xff\xd8\xff'):
                        mime = "image/jpeg"
                    else:
                        mime = "application/pdf"  # Default
                    print(f"[URL DOWNLOAD] Detected MIME type from content: {mime}")
            else:
                print(f"[URL DOWNLOAD] MIME type from header: {mime}")
            
            return file_bytes, mime
    except httpx.HTTPError as e:
        print(f"[ERROR] Failed to download URL: {str(e)}")
        raise ValueError(f"Failed to download document from URL: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Unexpected error downloading URL: {str(e)}")
        raise ValueError(f"Failed to download document from URL: {str(e)}")


async def prepare_pages(document_url: str):
    """
    Download document from URL and process it the same way as file uploads.
    This ensures consistent processing for both URLs and file uploads.
    """
    print(f"[URL PROCESSING] Processing URL input (downloading and processing like file upload)...")
    
    # Download the document from URL
    file_bytes, mime = await download_document(document_url)
    
    # Process it the same way as file uploads
    pages = process_uploaded_file(file_bytes, mime)
    
    print(f"[URL PROCESSING] URL processed - {len(pages)} page(s) ready")
    return pages


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
