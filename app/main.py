import asyncio
from fastapi import FastAPI
from app.schemas import InputBody, SuccessResponse, DataPayload, PageLineItems, BillItem, TokenUsage
from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm

app = FastAPI()

# Global lock → ensures ONE document is processed at a time
PROCESS_LOCK = asyncio.Lock()


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(body: InputBody):

    async with PROCESS_LOCK:
        pages = await prepare_pages(body.document)

        page_items = []
        total_tokens = input_tokens = output_tokens = 0

        # Process pages sequentially
        for page_no, img_bytes, mime in pages:
            extracted, usage = await extract_page_items_with_llm(img_bytes, page_no)

            items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"]
                )
                for i in extracted["bill_items"]
            ]

            page_items.append(
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
                pagewise_line_items=page_items,
                total_item_count=sum(len(p.bill_items) for p in page_items)
            )
        )
