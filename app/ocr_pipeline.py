# app/ocr_pipeline.py

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

    print("[PDF] Converting PDF → PNG @ 150 DPI")

    # Fastest + accurate conversion (no RGB conversion)
    pages = convert_from_bytes(
        file_bytes,
        dpi=150,
        fmt="png",           # keep PNG
        grayscale=False,     # keep original
        thread_count=2       # improves speed on Render
    )

    output = []
    for idx, page in enumerate(pages, start=1):

        # No RGB → better accuracy + faster
        buf = io.BytesIO()
        page.save(buf, format="PNG", optimize=False)

        output.append((idx, buf.getvalue()))

    print(f"[PAGES] Ready: {len(output)} pages")
    return output
