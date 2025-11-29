from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional

from app.schemas import (
    SuccessResponse,
    ErrorResponse,
    TokenUsage,
    DataPayload,
    PageLineItems,
    BillItem,
)

from app.ocr_pipeline import prepare_pages, process_uploaded_file
from app.llm_client import extract_page_items_with_llm

app = FastAPI(
    title="Bill Extraction API",
    docs_url=None,      # Disable Swagger UI
    redoc_url=None,     # Disable Redoc
    openapi_url=None    # Hide OpenAPI spec
)


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(
    document_url: Optional[str] = Form(None),
    document_file: Optional[UploadFile] = File(None),
):
    """
    Single unified endpoint.
    Accepts either:
      - document_url (PDF/image URL)
      - document_file (PDF/image upload)
    """
    try:
        # Validate input
        if document_url and document_file:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Provide either document_url OR document_file, not both."
                ).dict()
            )

        if not document_url and not document_file:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Input required: provide document_url or document_file."
                ).dict()
            )

        # Process URL input
        if document_url:
            pages = await prepare_pages(document_url)

        # Process uploaded file
        else:
            file_bytes = await document_file.read()
            pages = process_uploaded_file(file_bytes, document_file.content_type)

        # Extract items from each page
        pagewise_line_items = []
        total_tokens = input_tokens = output_tokens = 0

        for page_no, (img_bytes, mime) in pages:
            extracted, usage = extract_page_items_with_llm(img_bytes, page_no, mime)

            # Convert extracted items to schema
            items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"]
                )
                for i in extracted.get("bill_items", [])
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=extracted["page_type"],
                    bill_items=items
                )
            )

            # Accumulate token usage
            total_tokens += usage["total_tokens"]
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ),
            data=DataPayload(
                pagewise_line_items=pagewise_line_items,
                total_item_count=sum(len(p.bill_items) for p in pagewise_line_items)
            )
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                is_success=False,
                message=str(e)
            ).dict()
        )
