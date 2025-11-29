from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from app.schemas import (
    RequestBody,
    SuccessResponse,
    ErrorResponse,
    TokenUsage,
    DataPayload,
    PageLineItems,
    BillItem,
)

from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm

app = FastAPI(title="HackRx Bill Extraction API")


class URLRequest(BaseModel):
    """Request model for JSON body with URL"""
    document_url: str


@app.get("/")
async def root():
    """Health check endpoint - use this to verify API is running"""
    return {
        "status": "ok",
        "message": "Bill Extraction API is running",
        "endpoints": {
            "extract_bill_data": "POST /extract-bill-data (Form-data)",
            "extract_bill_data_json": "POST /extract-bill-data-json (JSON body)",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "Bill Extraction API"}


async def extract_bill_data_internal(
    document_url: Optional[str] = None,
    document_file: Optional[UploadFile] = None
):
    """Internal function that handles the actual extraction logic"""
    try:
        print("=" * 80)
        print("[REQUEST RECEIVED] New bill extraction request received")
        print("=" * 80)
        
        # Validate input: if file is uploaded, document_url must be null/empty
        if document_file:
            print(f"[INPUT TYPE] File upload detected")
            print(f"[FILE INFO] Filename: {document_file.filename}")
            print(f"[FILE INFO] Content-Type: {document_file.content_type}")
            
            # When file is uploaded, ensure document_url is null/empty
            if document_url and str(document_url).strip():
                print(f"[ERROR] document_url provided: {document_url[:100]}... (should be empty when file uploaded)")
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        is_success=False,
                        message="When uploading a file, 'document_url' must be empty/null. Please remove document_url or use URL input only."
                    ).dict()
                )
            print(f"[VALIDATION] document_url is empty/null (correct)")
        elif not document_url or not str(document_url).strip():
            # No file and no valid URL
            print(f"[ERROR] No valid input provided - both document_url and document_file are missing/empty")
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Please provide either 'document_url' (non-empty) or 'document_file', but not both"
                ).dict()
            )
        
        # Get document content based on input type
        if document_url and str(document_url).strip():
            # Handle URL input - pass URL directly to Gemini
            print(f"[INPUT TYPE] URL input detected")
            print(f"[URL] {document_url[:200]}{'...' if len(document_url) > 200 else ''}")
            pages = await prepare_pages(str(document_url))
            print(f"[PAGES] Processing {len(pages)} page(s) from URL")
        else:
            # Handle file upload - process all pages for PDFs
            print(f"[PROCESSING] Reading uploaded file...")
            from app.ocr_pipeline import process_uploaded_file
            file_bytes = await document_file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)
            print(f"[FILE INFO] File size: {file_size_mb:.2f} MB ({len(file_bytes)} bytes)")
            
            # Detect MIME type
            import mimetypes
            mime = document_file.content_type or "application/pdf"
            if mime == "application/octet-stream":
                detected_mime, _ = mimetypes.guess_type(document_file.filename or "")
                if detected_mime:
                    mime = detected_mime
                    print(f"[FILE INFO] Detected MIME type: {mime} (from filename)")
            
            print(f"[FILE INFO] MIME type: {mime}")
            
            # Process file - converts PDF to all pages or single image
            print(f"[PROCESSING] Processing file (converting PDF pages or preparing image)...")
            pages = process_uploaded_file(file_bytes, mime)
            print(f"[PAGES] Found {len(pages)} page(s) to process")
        
        print("-" * 80)

        pagewise_line_items = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        print(f"[PROCESSING] Starting extraction for {len(pages)} page(s)...")
        for idx, (page_no, page_data) in enumerate(pages, 1):
            print(f"[PAGE {idx}/{len(pages)}] Processing page {page_no}...")
            # page_data can be either URL (str) or image_bytes (bytes)
            # For URLs, page_data is a string. For file uploads, it's (image_bytes, mime) tuple
            if isinstance(page_data, tuple):
                # File upload: (image_bytes, mime)
                image_bytes, mime = page_data
                print(f"[PAGE {idx}/{len(pages)}] Sending image bytes ({len(image_bytes)} bytes) to Gemini AI...")
                page_extracted, usage = extract_page_items_with_llm(
                    image_bytes, page_no, mime
                )
            else:
                # URL: page_data is a string
                print(f"[PAGE {idx}/{len(pages)}] Sending URL to Gemini AI...")
                page_extracted, usage = extract_page_items_with_llm(
                    page_data, page_no
                )
            
            item_count = len(page_extracted.get("bill_items", []))
            print(f"[PAGE {idx}/{len(pages)}] Extracted {item_count} bill item(s) from page {page_no}")

            page_items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"],
                )
                for i in page_extracted.get("bill_items", [])
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=page_extracted["page_type"],
                    bill_items=page_items,
                )
            )

            total_tokens += usage["total_tokens"]
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

        total_item_count = sum(len(p.bill_items) for p in pagewise_line_items)

        print("-" * 80)
        print(f"[COMPLETED] Processing finished successfully!")
        print(f"[RESULTS] Total pages processed: {len(pagewise_line_items)}")
        print(f"[RESULTS] Total items extracted: {total_item_count}")
        print(f"[RESULTS] Total tokens used: {total_tokens} (input: {input_tokens}, output: {output_tokens})")
        print("=" * 80)

        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            data=DataPayload(
                pagewise_line_items=pagewise_line_items,
                total_item_count=total_item_count,
            ),
        )

    except Exception as e:
        print("-" * 80)
        print(f"[ERROR] Exception occurred: {str(e)}")
        print(f"[ERROR] Type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(is_success=False, message=str(e)).dict()
        )


@app.post("/extract-bill-data-json", response_model=SuccessResponse)
async def extract_bill_data_json(request: URLRequest):
    """
    Extract bill data from PDF or image URL using JSON body.
    
    **Example with curl:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data-json \
      -H "Content-Type: application/json" \
      -d '{"document_url": "https://example.com/bill.pdf"}'
    ```
    """
    return await extract_bill_data_internal(document_url=request.document_url, document_file=None)


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(
    document_url: Optional[str] = Form(None, description="URL to PDF or image (http/https)"),
    document_file: Optional[UploadFile] = File(None, description="Upload PDF or image file directly")
):
    """
    Extract bill data from PDF or image (Form-data).
    
    **For URL input:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data \
      -F "document_url=https://example.com/bill.pdf"
    ```
    
    **For file upload:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data \
      -F "document_file=@bill.pdf"
    ```
    
    **For JSON body (alternative):**
    Use `/extract-bill-data-json` endpoint instead.
    """
    return await extract_bill_data_internal(document_url=document_url, document_file=document_file)
