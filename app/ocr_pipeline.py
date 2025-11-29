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

        # auto detect MIME
        if not mime or mime == "application/octet-stream":
            guess, _ = mimetypes.guess_type(url)
            if guess:
                mime = guess
        if not mime:
            mime = "application/pdf"

        return file_bytes, mime

    except Exception as e:
        print("[ERROR] URL download failed:", e)
        raise ValueError("Unable to download file from URL")


async def prepare_pages(url: str):
    file_bytes, mime = await download_document(url)
    return process_uploaded_file(file_bytes, mime)


def process_uploaded_file(file_bytes: bytes, mime: str):
    pages = []

    if "pdf" in mime.lower():
        print("[PDF] Converting PDF → PNG (DPI=200)")
        images = convert_from_bytes(file_bytes, dpi=200)

        for idx, img in enumerate(images, start=1):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages.append((idx, (buf.getvalue(), "image/png")))

    elif "image" in mime.lower():
        print("[IMAGE] Single image input")

        if mime != "image/png":
            img = Image.open(io.BytesIO(file_bytes))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pages.append((1, (buf.getvalue(), "image/png")))
        else:
            pages.append((1, (file_bytes, mime)))

    else:
        raise ValueError(f"Unsupported file type: {mime}")

    print(f"[PAGES] Prepared {len(pages)} pages")
    return pages
