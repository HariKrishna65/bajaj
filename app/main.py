import asyncio
from fastapi import FastAPI
from app.ocr_pipeline import prepare_pages
from app.llm_client import extract_page_items_with_llm
from app.schemas import *

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/extract-bill-data")
async def extract_bill_data(body: InputBody):
    try:
        pages = await prepare_pages(body.document)

        # Create parallel tasks for each page → Gemini
        tasks = [
            extract_page_items_with_llm(img_bytes, page_no, mime)
            for page_no, (img_bytes, mime) in pages
        ]

        results = await asyncio.gather(*tasks)

        page_items = []
        total_tok = inp = out = 0

        for (extracted, usage) in results:
            items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"]
                )
                for i in extracted.get("bill_items", [])
            ]

            page_items.append(
                PageLineItems(
                    page_no=extracted["page_no"],
                    page_type=extracted["page_type"],
                    bill_items=items
                )
            )

            total_tok += usage["total_tokens"]
            inp += usage["input_tokens"]
            out += usage["output_tokens"]

        return SuccessResponse(
            is_success=True,
            token_usage=TokenUsage(
                total_tokens=total_tok,
                input_tokens=inp,
                output_tokens=out
            ),
            data=DataPayload(
                pagewise_line_items=page_items,
                total_item_count=sum(len(p.bill_items) for p in page_items)
            )
        )

    except Exception as e:
        return {"error": str(e)}
