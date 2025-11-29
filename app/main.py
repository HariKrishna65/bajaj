from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.schemas import SuccessResponse, ErrorResponse, TokenUsage, DataPayload, PageLineItems, BillItem
from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm

app = FastAPI(
    title="Bill Extraction API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(payload: dict):
    """
    HackRx format:
    POST /extract-bill-data
    Content-Type: application/json

    {
        "document": "https://example.com/file.pdf"
    }
    """
    try:
        if "document" not in payload:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Missing required field: document"
                ).dict()
            )

        document_url = payload["document"].strip()
        print(f"[REQUEST] URL = {document_url}")

        # Convert PDF/image URL → Pages
        pages = await prepare_pages(document_url)

        pagewise_line_items = []
        total_tokens = input_tokens = output_tokens = 0

        for page_no, (img_bytes, mime) in pages:
            extracted, usage = extract_page_items_with_llm(img_bytes, page_no, mime)

            items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"]
                )
                for i in extracted["bill_items"]
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=extracted["page_type"],
                    bill_items=items
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
                output_tokens=output_tokens
            ),
            data=DataPayload(
                pagewise_line_items=pagewise_line_items,
                total_item_count=sum(len(p.bill_items) for p in pagewise_line_items)
            )
        )

    except Exception as e:
        print("[ERROR]", e)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                is_success=False,
                message=str(e)
            ).dict()
        )
