import httpx
from pdf2image import convert_from_bytes
import io


async def download_file(url: str) -> bytes:
    print("[URL DOWNLOAD] Fetching:", url)

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


async def prepare_pages(url: str):
    pdf_bytes = await download_file(url)

    print("[PDF] Converting PDF → PNG (DPI=200)")

    images = convert_from_bytes(
        pdf_bytes,
        dpi=200,
        fmt="png",
        thread_count=1
    )

    pages = []
    for i, img in enumerate(images, 1):
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        pages.append((i, buffer.getvalue(), "image/png"))

    print(f"[PAGES] Prepared {len(pages)} pages")
    return pages
