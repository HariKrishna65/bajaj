from fastapi import FastAPI
from app.schemas import (
    SuccessResponse, ErrorResponse,
    TokenUsage, PageLineItems, BillItem, DataPayload
)
from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm


app = FastAPI()


@app.post("/extract-bill-data")
async def extract_bill_data(body: dict):
    url = body.get("document")
    if not url:
        return ErrorResponse(is_success=False, message="document URL required")

    try:
        pages = await prepare_pages(url)

        page_items = []
        t_total = t_in = t_out = 0

        # Process pages strictly one-by-one
        for page_no, img_bytes in pages:
            data, usage = extract_page_items_with_llm(img_bytes, page_no)

            items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"]
                ) for i in data["bill_items"]
            ]

            page_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=data["page_type"],
                    bill_items=items
                )
            )

            t_total += usage["total_tokens"]
            t_in += usage["input_tokens"]
            t_out += usage["output_tokens"]

        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=t_total,
                input_tokens=t_in,
                output_tokens=t_out
            ),
            data=DataPayload(
                pagewise_line_items=page_items,
                total_item_count=sum(len(p.bill_items) for p in page_items)
            )
        )

    except Exception as e:
        return ErrorResponse(is_success=False, message=str(e))
