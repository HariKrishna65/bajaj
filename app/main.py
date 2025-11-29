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
    docs_url=None,     # Disable Swagger UI
    redoc_url=None,    # Disable Redoc
    openapi_url=None   # Hide OpenAPI spec (optional)
)


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(
    document_url: Optional[str] = Form(None),
    document_file: Optional[UploadFile] = File(None),
):
    """
    ONLY ENDPOINT (form-data only)
    Supports:
      - document_url (string)
      - document_file (file upload)
    """
    try:
        # Validation
        if document_url and document_file:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Provide either document_url or document_file, not both."
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

        # Process URL
        if document_url:
            pages = await prepare_pages(document_url)

        # Process file
        else:
            file_bytes = await document_file.read()
            pages = process_uploaded_file(file_bytes, document_file.content_type)

        # Extract items page-wise
        pagewise_line_items = []
        total_tokens = input_tokens = output_tokens = 0

        for page_no, (img_bytes, mime) in pages:
            extracted, usage = extract_page_items_with_llm(img_bytes, page_no, mime)

            page_items = []
            for item in extracted.get("bill_items", []):
                page_items.append(
                    BillItem(
                        item_name=item["item_name"],
                        item_amount=item["item_amount"],
                        item_rate=item["item_rate"],
                        item_quantity=item["item_quantity"]
                    )
                )

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=extracted["page_type"],
                    bill_items=page_items
                )
            )

            total_tokens += usage["total_tokens"]
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            data=DataPayload(
                pagewise_line_items=pagewise_line_items,
                total_item_count=sum(len(x.bill_items) for x in pagewise_line_items)
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
