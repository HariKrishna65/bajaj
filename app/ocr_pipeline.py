import io
import mimetypes
import httpx
from typing import List, Tuple
from pdf2image import convert_from_bytes
from PIL import Image


async def download_document(url: str) -> Tuple[bytes, str]:
    print(f"[URL DOWNLOAD] Fetching: {url}")

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()

        file_bytes = r.content
        mime = r.headers.get("content-type", "").split(";")[0]

        # Detect from URL
        if not mime or mime == "application/octet-stream":
            detected, _ = mimetypes.guess_type(url)
            if detected:
                mime = detected

        if not mime:
            mime = "application/pdf"

        return file_bytes, mime

    except Exception as e:
        print("[ERROR] URL download failed:", e)
        raise ValueError("Unable to download file from URL")


async def prepare_pages(url: str):
    """Download a PDF/image URL and convert into pages."""
    file_bytes, mime = await download_document(url)
    return process_uploaded_file(file_bytes, mime)


def process_uploaded_file(file_bytes: bytes, mime: str) -> List[Tuple[int, Tuple[bytes, str]]]:
    pages = []

    # ----------------------------------------------------
    # PDF INPUT → PNG IMAGES (DPI = 200)
    # ----------------------------------------------------
    if "pdf" in mime.lower():
        print("[PDF] Converting PDF → PNG images (DPI = 200)...")

        # 🔥 Requested DPI 200
        pdf_images = convert_from_bytes(file_bytes, dpi=200)

        for idx, img in enumerate(pdf_images, start=1):
            buffer = io.BytesIO()

            # PNG — as requested
            img.save(buffer, format="PNG")

            pages.append((idx, (buffer.getvalue(), "image/png")))

        print(f"[PDF] Total pages extracted: {len(pdf_images)}")

    # ----------------------------------------------------
    # IMAGE INPUT → pass through (ensure PNG)
    # ----------------------------------------------------
    elif "image" in mime.lower():
        print("[IMAGE] Single image detected.")

        if mime != "image/png":
            # Convert uploaded image to PNG for consistency
            img = Image.open(io.BytesIO(file_bytes))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            pages.append((1, (buffer.getvalue(), "image/png")))
        else:
            pages.append((1, (file_bytes, mime)))

    else:
        raise ValueError(f"Unsupported file type: {mime}")

    print(f"[PAGES] Ready for LLM: {len(pages)} pages")
    return pages
