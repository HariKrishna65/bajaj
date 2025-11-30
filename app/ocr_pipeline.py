import io
import httpx
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np


async def download_document(url: str) -> bytes:
    print(f"[DOWNLOAD] {url}")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


def enhance_image_pillow(img_bytes: bytes) -> bytes:
    """Enhance PNG using Pillow (Render-compatible)."""

    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except:
        print("[WARNING] Pillow failed to load image — returning original")
        return img_bytes

    # --- 1. Reduce yellow tint ---
    r, g, b = img.split()
    # Increase blue, reduce red → removes yellow
    r = r.point(lambda p: p * 0.85)
    g = g.point(lambda p: p * 0.95)
    b = b.point(lambda p: min(255, p * 1.15))
    img = Image.merge("RGB", (r, g, b))

    # --- 2. Increase contrast ---
    img = ImageEnhance.Contrast(img).enhance(2.2)

    # --- 3. Increase sharpness for handwriting ---
    img = ImageEnhance.Sharpness(img).enhance(2.5)

    # --- 4. Small denoise ---
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Convert back to PNG bytes
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


async def prepare_pages(url: str):
    """Download → Convert PDF → Enhance pages (NO opencv)."""

    file_bytes = await download_document(url)

    print("[PDF] Converting PDF → PNG @ 150 DPI")

    pages = convert_from_bytes(
        file_bytes,
        fmt="png",
        dpi=150
    )

    output = []

    for idx, page in enumerate(pages, start=1):
        buf = io.BytesIO()
        page.save(buf, format="PNG")
        raw_png = buf.getvalue()

        enhanced_png = enhance_image_pillow(raw_png)

        output.append((idx, enhanced_png))

    print(f"[PAGES] Ready: {len(output)} pages")
    return output
