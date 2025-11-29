import io
import httpx
from pdf2image import convert_from_bytes


async def download_document(url: str) -> bytes:
    print(f"[DOWNLOAD] {url}")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


async def prepare_pages(url: str):
    file_bytes = await download_document(url)

    print("[PDF] Converting PDF → PNG @ 200 DPI")

    pages = convert_from_bytes(
        file_bytes,
        fmt="png",
        dpi=200
    )

    output = []
    for idx, page in enumerate(pages, start=1):
        buf = io.BytesIO()
        page.save(buf, format="PNG")
        output.append((idx, buf.getvalue()))

    print(f"[PAGES] Ready: {len(output)} pages")
    return output
