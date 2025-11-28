import json
import os
import base64
import httpx
from typing import Tuple, Dict, Any

# Read GEMINI key from environment (try both GEMINI_API_KEY and GOOGLE_API_KEY)
def get_api_key():
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

SYSTEM_PROMPT = """
You are an expert medical bill analyzer.

Extract ONLY the line items from the bill image.

Return ONLY this JSON structure:

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

STRICT RULES:
1. Do NOT include: subtotal, total, tax, discount, headers, notes
2. item_name: EXACT text from document
3. item_quantity: EXACT value, or 1 if missing
4. item_rate: EXACT rate from document
5. item_amount: EXACT final line amount
6. page_type MUST BE:
   - Pharmacy → for medicines
   - Bill Detail → hospital/services/tests
   - Final Bill → summary page
7. If no items exist, return empty array
8. ONLY JSON OUTPUT, no explanation
"""


def extract_page_items_with_llm(
    image_bytes: bytes,
    page_no: int,
    mime: str = "image/png"
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    
    api_key = get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set")
    
    # Encode image to base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Try different model names via REST API
    # Try v1beta API (where newer models are available)
    api_versions = ["v1beta"]
    model_names = [
        "gemini-2.0-flash",      # Fast and efficient
        "gemini-2.5-flash",      # Latest flash model
        "gemini-flash-latest",   # Auto-updates to latest
        "gemini-2.5-pro",        # More capable
        "gemini-pro-latest",     # Auto-updates to latest pro
    ]
    
    url_template = "https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={key}"
    
    # Create payload - response_mime_type is only available in v1beta
    payload_base = {
        "contents": [{
            "parts": [
                {"text": SYSTEM_PROMPT},
                {
                    "inline_data": {
                        "mime_type": mime,
                        "data": image_base64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1
        }
    }
    
    # Add response_mime_type only for v1beta
    payload_v1beta = {
        **payload_base,
        "generationConfig": {
            **payload_base["generationConfig"],
            "response_mime_type": "application/json"
        }
    }
    
    errors = []
    for api_version in api_versions:
        # Use appropriate payload for each API version
        payload = payload_v1beta if api_version == "v1beta" else payload_base
        for model_name in model_names:
            try:
                url = url_template.format(version=api_version, model=model_name, key=api_key)
                print(f"  Trying {api_version}/{model_name}...")
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        
                        # Cleanup formatting if Gemini adds code blocks
                        raw_text = content.strip()
                        if raw_text.startswith("```"):
                            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                        
                        page_data = json.loads(raw_text)
                        page_data["page_no"] = str(page_no)
                        
                        # Extract usage info if available
                        usage_info = result.get('usageMetadata', {})
                        usage = {
                            "total_tokens": usage_info.get('totalTokenCount', 0),
                            "input_tokens": usage_info.get('promptTokenCount', 0),
                            "output_tokens": usage_info.get('candidatesTokenCount', 0)
                        }
                        
                        print(f"  [OK] Successfully used {api_version}/{model_name}")
                        return page_data, usage
                    else:
                        error_msg = f"{api_version}/{model_name}: No candidates in response"
                        errors.append(error_msg)
                        print(f"  [FAIL] {error_msg}")
                elif response.status_code == 404:
                    error_text = response.text[:300] if hasattr(response, 'text') else str(response.content[:300])
                    error_msg = f"{api_version}/{model_name}: Model not found (404) - {error_text}"
                    errors.append(error_msg)
                    print(f"  [FAIL] {error_msg}")
                    # Continue to next model/version
                else:
                    error_text = response.text[:300]
                    error_msg = f"{api_version}/{model_name}: API error ({response.status_code}) - {error_text}"
                    errors.append(error_msg)
                    print(f"  [FAIL] {error_msg}")
            except json.JSONDecodeError as e:
                error_msg = f"{api_version}/{model_name}: JSON decode error - {str(e)}"
                errors.append(error_msg)
                print(f"  [FAIL] {error_msg}")
            except Exception as e:
                error_msg = f"{api_version}/{model_name}: Exception - {str(e)[:200]}"
                errors.append(error_msg)
                print(f"  [FAIL] {error_msg}")
    
    all_errors = "\n".join(errors) if errors else "No errors captured"
    raise ValueError(f"Could not process image with any model. Errors:\n{all_errors}")
