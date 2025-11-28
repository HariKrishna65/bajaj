import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# USE THIS MODEL (compatible with version 0.3.2)
model = genai.GenerativeModel("models/gemini-pro-vision")

SYSTEM_PROMPT = """
You are an expert bill analyzer.

The input is a PUBLIC URL to a bill image or PDF.
Read the document and extract ONLY LINE ITEMS.

Return ONLY valid JSON in this exact format:

{
  "page_no": "string",
  "page_type": "Bill Detail | Final Bill | Pharmacy",
  "bill_items": [
     {
       "item_name": "string",
       "item_amount": float,
       "item_rate": float,
       "item_quantity": float
     }
  ]
}

RULES:
- Do NOT include total, subtotal, tax, discount
- item_quantity if missing use 1
- page_type must be ONLY:
  Bill Detail, Final Bill, Pharmacy
- Output ONLY pure JSON
"""

def extract_page_items_with_llm(document_url: str, page_no: str):

    response = model.generate_content([
        SYSTEM_PROMPT,
        f"Extract line items from this document URL: {document_url}"
    ])

    raw_text = response.text.strip()

    # Cleanup any code fences
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    page_data = json.loads(raw_text)
    page_data["page_no"] = page_no

    usage = {
        "total_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0
    }

    return page_data, usage
