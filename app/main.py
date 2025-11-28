from fastapi import FastAPI
from fastapi.responses import JSONResponse

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
async def extract_bill_data(body: RequestBody):

    try:
        pages = await prepare_pages(str(body.document))

        pagewise_line_items = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        for page_no, document_url in pages:

            page_data, usage = extract_page_items_with_llm(
                document_url, page_no
            )

            page_items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"],
                )
                for i in page_data.get("bill_items", [])
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=page_data["page_type"],
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
