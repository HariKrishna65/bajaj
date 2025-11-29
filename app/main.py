from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse

from app.schemas import (
    SuccessResponse,
    ErrorResponse,
    TokenUsage,
    DataPayload,
    PageLineItems,
    BillItem,
)

from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm


app = FastAPI(
    title="Bill Extraction API",
    docs_url=None,      # Disable Swagger UI
    redoc_url=None,     # Disable Redoc
    openapi_url=None    # Hide OpenAPI spec
)


@app.post("/extract-bill-data")
async def extract_bill_data(document_url: str = Form(...)):
    """
    Accept PDF or Image URL only.
    Only one input is allowed: document_url
    """
    try:
        # STEP 1: Download and prepare pages (PDF → images)
        pages = await prepare_pages(document_url)

        pagewise_line_items = []
        total_tokens = input_tokens = output_tokens = 0

        # STEP 2: Process each page through LLM
        for page_no, (img_bytes, mime) in pages:
            extracted, usage = extract_page_items_with_llm(
                img_bytes, page_no, mime
            )

            # Convert into response schema
            items = [
                BillItem(
                    item_name=x["item_name"],
                    item_amount=x["item_amount"],
                    item_rate=x["item_rate"],
                    item_quantity=x["item_quantity"],
                )
                for x in extracted["bill_items"]
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=extracted["page_type"],
                    bill_items=items,
                )
            )

            # Token accumulation
            total_tokens += usage["total_tokens"]
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

        # STEP 3: Return the final structured response
        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            data=DataPayload(
                pagewise_line_items=pagewise_line_items,
                total_item_count=sum(len(p.bill_items) for p in pagewise_line_items),
            ),
        )

    except Exception as e:
        # Return proper error object
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                is_success=False,
                message=str(e)
            ).dict()
        )
