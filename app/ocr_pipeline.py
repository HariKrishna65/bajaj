import io
import httpx
import cv2
import numpy as np
from pdf2image import convert_from_bytes


# ------------------------------
# DOWNLOAD DOCUMENT (ASYNC)
# ------------------------------
async def download_document(url: str) -> bytes:
    print(f"[DOWNLOAD] {url}")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


# ------------------------------
# ENHANCE IMAGE FOR HANDWRITING
# ------------------------------
def enhance_image(img_bytes: bytes) -> bytes:
    """Cleans yellow background, sharpens handwriting, improves contrast."""

    # Read PNG bytes → OpenCV image
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # --- Guard: corrupted page ---
    if img is None:
        print("[WARNING] Could not decode image, returning original")
        return img_bytes

    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Remove yellow background using adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11
    )

    # 3. Denoise handwriting strokes
    den = cv2.fastNlMeansDenoising(thresh, h=35)

    # 4. Sharpen handwriting edges
    kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ])
    sharp = cv2.filter2D(den, -1, kernel)

    # Convert back to PNG
    ok, out_png = cv2.imencode(".png", sharp)
    if not ok:
        print("[WARNING] Failed to encode enhanced PNG, returning raw image")
        return img_bytes

    return out_png.tobytes()


# ------------------------------
# PREPARE PAGES (PDF → ENHANCED PNG)
# ------------------------------
async def prepare_pages(url: str):
    """Downloads PDF → converts pages → enhances → returns list of (page_no, png_bytes)."""

    file_bytes = await download_document(url)

    print("[PDF] Converting PDF → PNG @ 150 DPI")
    pages = convert_from_bytes(
        file_bytes,
        fmt="png",
        dpi=150
    )

    out_pages = []

    for idx, page in enumerate(pages, start=1):
        # Convert PIL → raw PNG bytes
        buf = io.BytesIO()
        page.save(buf, format="PNG")
        raw_png = buf.getvalue()

        # Enhance for handwriting (yellow removal + sharpening)
        cleaned_png = enhance_image(raw_png)

        out_pages.append((idx, cleaned_png))

    print(f"[PAGES] Ready after enhancement → {len(out_pages)} pages")
    return out_pages
