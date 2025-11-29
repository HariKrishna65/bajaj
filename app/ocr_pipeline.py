import io
import mimetypes
from typing import List, Tuple
from pdf2image import convert_from_bytes


async def download_document(url: str):
    print("[URL DOWNLOAD] Fetching:", url)

    import httpx
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(url)
        res.raise_for_status()

    file_bytes = res.content
    mime = res.headers.get("content-type", "").split(";")[0]

    if not mime or mime == "application/octet-stream":
        guess, _ = mimetypes.guess_type(url)
        mime = guess or "application/pdf"

    return file_bytes, mime


async def prepare_pages(url: str) -> List[Tuple[str, Tuple[bytes, str]]]:
    file_bytes, mime = await download_document(url)

    if "pdf" in mime:
        print("[PDF] Converting PDF → PNG (DPI=180)")
        images = convert_from_bytes(file_bytes, dpi=180)
        pages = []
        for i, img in enumerate(images, 1):
            buff = io.BytesIO()
            img.save(buff, format="PNG")
            pages.append((str(i), buff.getvalue()))
        print(f"[PAGES] Prepared {len(pages)} pages")
        return [(p[0], (p[1], "image/png")) for p in pages]

    else:
        print("[IMAGE] Single image")
        return [("1", (file_bytes, mime))]
