import io
import httpx
from pdf2image import convert_from_bytes


async def download_document(url: str) -> bytes:
    """
    Download the PDF file from the given URL.
    """
    print(f"[DOWNLOAD] {url}")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def prepare_pages(url: str):
    """
    Download PDF → Convert to PNG pages (DPI = 130 for speed)
    Returns list: [(page_no, image_bytes), ...]
    """

    file_bytes = await download_document(url)

    print("[PDF] Converting PDF → PNG @ 130 DPI (Fast Mode)")

    # Convert the PDF to PNG images
    pages = convert_from_bytes(
        file_bytes,
        fmt="png",
        dpi=130   # optimized DPI
    )

    output_pages = []

    for idx, page in enumerate(pages, start=1):
        buffer = io.BytesIO()
        page.save(buffer, format="PNG")  # always PNG
        output_pages.append((idx, buffer.getvalue()))

    print(f"[PAGES] Ready: {len(output_pages)} page(s)")
    return output_pages
