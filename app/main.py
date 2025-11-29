from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

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


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(
    document_url: Optional[str] = Form(None, description="URL to PDF or image (http/https)"),
    document_file: Optional[UploadFile] = File(None, description="Upload PDF or image file directly")
):
    """
    Extract bill data from PDF or image.
    
    Accepts either:
    - document_url: URL to PDF or image file (e.g., https://example.com/bill.pdf)
    - document_file: Upload PDF or image file directly
    
    Supports:
    - PDF URLs (http/https)
    - Image URLs (http/https) 
    - Local PDF file uploads
    - Local image file uploads (jpg, png, etc.)
    """
    try:
        # Validate input: if file is uploaded, document_url must be null/empty
        if document_file:
            # When file is uploaded, ensure document_url is null/empty
            if document_url and str(document_url).strip():
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        is_success=False,
                        message="When uploading a file, 'document_url' must be empty/null. Please remove document_url or use URL input only."
                    ).dict()
                )
        elif not document_url or not str(document_url).strip():
            # No file and no valid URL
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
            pages = await prepare_pages(str(document_url))
        else:
            # Handle file upload - process all pages for PDFs
            from app.ocr_pipeline import process_uploaded_file
            file_bytes = await document_file.read()
            # Detect MIME type
            import mimetypes
            mime = document_file.content_type or "application/pdf"
            if mime == "application/octet-stream":
                detected_mime, _ = mimetypes.guess_type(document_file.filename or "")
                if detected_mime:
                    mime = detected_mime
            
            # Process file - converts PDF to all pages or single image
            pages = process_uploaded_file(file_bytes, mime)

        pagewise_line_items = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        for page_no, page_data in pages:
            # page_data can be either URL (str) or image_bytes (bytes)
            # For URLs, page_data is a string. For file uploads, it's (image_bytes, mime) tuple
            if isinstance(page_data, tuple):
                # File upload: (image_bytes, mime)
                image_bytes, mime = page_data
                page_extracted, usage = extract_page_items_with_llm(
                    image_bytes, page_no, mime
                )
            else:
                # URL: page_data is a string
                page_extracted, usage = extract_page_items_with_llm(
                    page_data, page_no
                )

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
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(is_success=False, message=str(e)).dict()
        )
