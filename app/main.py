from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Optional
from pydantic import BaseModel

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


class URLRequest(BaseModel):
    """Request model for JSON body with URL"""
    document_url: str


@app.get("/", response_class=HTMLResponse)
async def root_get():
    """Interactive form interface for bill extraction"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bill Extraction API</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 700px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 25px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }
        .description {
            color: #666;
            font-size: 12px;
            margin-bottom: 8px;
            font-weight: normal;
        }
        input[type="text"], input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        input[type="file"] {
            padding: 8px;
            cursor: pointer;
        }
        .checkbox-group {
            margin-top: 8px;
            display: flex;
            align-items: center;
        }
        .checkbox-group input[type="checkbox"] {
            margin-right: 8px;
            cursor: pointer;
        }
        .checkbox-group label {
            margin: 0;
            font-weight: normal;
            font-size: 13px;
            color: #666;
            cursor: pointer;
        }
        .content-type {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #666;
        }
        .content-type strong {
            color: #333;
        }
        .execute-btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .execute-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .execute-btn:active {
            transform: translateY(0);
        }
        .execute-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 6px;
            display: none;
        }
        .result pre {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            max-height: 500px;
            overflow-y: auto;
        }
        .error {
            background: #fee;
            border: 1px solid #fcc;
            color: #c00;
        }
        .success {
            background: #efe;
            border: 1px solid #cfc;
        }
        .info-links {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
        }
        .info-links a {
            color: #667eea;
            text-decoration: none;
            margin: 0 10px;
            font-size: 13px;
        }
        .info-links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Bill Extraction API</h1>
        <p class="subtitle">Extract bill line items from PDF or image documents using AI</p>
        
        <div class="content-type">
            <strong>Content-Type:</strong> multipart/form-data
        </div>
        
        <form id="extractForm" action="/extract-bill-data" method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label for="document_url">document_url</label>
                <div class="description">URL to PDF or image (http/https)</div>
                <input type="text" id="document_url" name="document_url" placeholder="https://example.com/bill.pdf">
                <div class="checkbox-group">
                    <input type="checkbox" id="url_empty" name="url_empty">
                    <label for="url_empty">Send empty value</label>
                </div>
            </div>
            
            <div class="form-group">
                <label for="document_file">document_file</label>
                <div class="description">Upload PDF or image file directly</div>
                <input type="file" id="document_file" name="document_file" accept=".pdf,.jpg,.jpeg,.png,.gif">
                <div class="checkbox-group">
                    <input type="checkbox" id="file_empty" name="file_empty" checked>
                    <label for="file_empty">Send empty value</label>
                </div>
            </div>
            
            <button type="submit" class="execute-btn" id="executeBtn">Execute</button>
        </form>
        
        <div class="loading" id="loading">Processing your request...</div>
        
        <div class="result" id="result"></div>
        
        <div class="info-links">
            <a href="/docs">API Documentation</a>
            <a href="/health">Health Check</a>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('extractForm');
        const executeBtn = document.getElementById('executeBtn');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            executeBtn.disabled = true;
            loading.style.display = 'block';
            result.style.display = 'none';
            
            const formData = new FormData();
            
            // Handle document_url
            const urlInput = document.getElementById('document_url');
            const urlEmpty = document.getElementById('url_empty').checked;
            if (!urlEmpty && urlInput.value.trim()) {
                formData.append('document_url', urlInput.value.trim());
            }
            
            // Handle document_file
            const fileInput = document.getElementById('document_file');
            const fileEmpty = document.getElementById('file_empty').checked;
            if (!fileEmpty && fileInput.files.length > 0) {
                formData.append('document_file', fileInput.files[0]);
            }
            
            try {
                const response = await fetch('/extract-bill-data', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                loading.style.display = 'none';
                result.style.display = 'block';
                
                if (response.ok) {
                    result.className = 'result success';
                    result.innerHTML = '<h3>✓ Success</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } else {
                    result.className = 'result error';
                    result.innerHTML = '<h3>✗ Error (' + response.status + ')</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                }
            } catch (error) {
                loading.style.display = 'none';
                result.style.display = 'block';
                result.className = 'result error';
                result.innerHTML = '<h3>✗ Error</h3><pre>' + error.message + '</pre>';
            } finally {
                executeBtn.disabled = false;
            }
        });
        
        // Auto-uncheck file empty when file is selected
        document.getElementById('document_file').addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                document.getElementById('file_empty').checked = false;
            }
        });
        
        // Auto-uncheck url empty when URL is entered
        document.getElementById('document_url').addEventListener('input', function(e) {
            if (e.target.value.trim()) {
                document.getElementById('url_empty').checked = false;
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/")
async def root_post():
    """Handle POST requests to root - redirect to proper endpoint"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Method not allowed",
            "message": "Please use POST /extract-bill-data endpoint or use the form interface at GET /",
            "endpoints": {
                "form_interface": "GET /",
                "extract_with_form": "POST /extract-bill-data",
                "extract_with_json": "POST /extract-bill-data-json",
                "docs": "GET /docs"
            }
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "Bill Extraction API"}


async def extract_bill_data_internal(
    document_url: Optional[str] = None,
    document_file: Optional[UploadFile] = None
):
    """Internal function that handles the actual extraction logic"""
    try:
        print("=" * 80)
        print("[REQUEST RECEIVED] New bill extraction request received")
        print("=" * 80)
        
        # Validate input: if file is uploaded, document_url must be null/empty
        if document_file:
            print(f"[INPUT TYPE] File upload detected")
            print(f"[FILE INFO] Filename: {document_file.filename}")
            print(f"[FILE INFO] Content-Type: {document_file.content_type}")
            
            # When file is uploaded, ensure document_url is null/empty
            if document_url and str(document_url).strip():
                print(f"[ERROR] document_url provided: {document_url[:100]}... (should be empty when file uploaded)")
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        is_success=False,
                        message="When uploading a file, 'document_url' must be empty/null. Please remove document_url or use URL input only."
                    ).dict()
                )
            print(f"[VALIDATION] document_url is empty/null (correct)")
        elif not document_url or not str(document_url).strip():
            # No file and no valid URL
            print(f"[ERROR] No valid input provided - both document_url and document_file are missing/empty")
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    is_success=False,
                    message="Please provide either 'document_url' (non-empty) or 'document_file', but not both"
                ).dict()
            )
        
        # Get document content based on input type
        if document_url and str(document_url).strip():
            # Handle URL input - pass URL directly to Gemini
            print(f"[INPUT TYPE] URL input detected")
            print(f"[URL] {document_url[:200]}{'...' if len(document_url) > 200 else ''}")
            pages = await prepare_pages(str(document_url))
            print(f"[PAGES] Processing {len(pages)} page(s) from URL")
        else:
            # Handle file upload - process all pages for PDFs
            print(f"[PROCESSING] Reading uploaded file...")
            from app.ocr_pipeline import process_uploaded_file
            file_bytes = await document_file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)
            print(f"[FILE INFO] File size: {file_size_mb:.2f} MB ({len(file_bytes)} bytes)")
            
            # Detect MIME type
            import mimetypes
            mime = document_file.content_type or "application/pdf"
            if mime == "application/octet-stream":
                detected_mime, _ = mimetypes.guess_type(document_file.filename or "")
                if detected_mime:
                    mime = detected_mime
                    print(f"[FILE INFO] Detected MIME type: {mime} (from filename)")
            
            print(f"[FILE INFO] MIME type: {mime}")
            
            # Process file - converts PDF to all pages or single image
            print(f"[PROCESSING] Processing file (converting PDF pages or preparing image)...")
            pages = process_uploaded_file(file_bytes, mime)
            print(f"[PAGES] Found {len(pages)} page(s) to process")
        
        print("-" * 80)

        pagewise_line_items = []
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0

        print(f"[PROCESSING] Starting extraction for {len(pages)} page(s)...")
        for idx, (page_no, page_data) in enumerate(pages, 1):
            print(f"[PAGE {idx}/{len(pages)}] Processing page {page_no}...")
            # page_data is always (image_bytes, mime) tuple for both URLs and file uploads
            # URLs are now downloaded and processed the same way as file uploads
            if isinstance(page_data, tuple):
                # Both URLs and file uploads: (image_bytes, mime)
                image_bytes, mime = page_data
                print(f"[PAGE {idx}/{len(pages)}] Sending image bytes ({len(image_bytes)} bytes) to Gemini AI...")
                page_extracted, usage = extract_page_items_with_llm(
                    image_bytes, page_no, mime
                )
            else:
                # Fallback: if somehow we get a string (shouldn't happen now)
                print(f"[PAGE {idx}/{len(pages)}] WARNING: Unexpected data type, treating as URL string...")
                page_extracted, usage = extract_page_items_with_llm(
                    page_data, page_no
                )
            
            item_count = len(page_extracted.get("bill_items", []))
            print(f"[PAGE {idx}/{len(pages)}] Extracted {item_count} bill item(s) from page {page_no}")

            page_items = [
                BillItem(
                    item_name=i["item_name"],
                    item_amount=i["item_amount"],
                    item_rate=i["item_rate"],
                    item_quantity=i["item_quantity"],
                )
                for i in page_extracted.get("bill_items", [])
            ]

            pagewise_line_items.append(
                PageLineItems(
                    page_no=str(page_no),
                    page_type=page_extracted["page_type"],
                    bill_items=page_items,
                )
            )

            total_tokens += usage["total_tokens"]
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

        total_item_count = sum(len(p.bill_items) for p in pagewise_line_items)

        print("-" * 80)
        print(f"[COMPLETED] Processing finished successfully!")
        print(f"[RESULTS] Total pages processed: {len(pagewise_line_items)}")
        print(f"[RESULTS] Total items extracted: {total_item_count}")
        print(f"[RESULTS] Total tokens used: {total_tokens} (input: {input_tokens}, output: {output_tokens})")
        print("=" * 80)

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
        print("-" * 80)
        print(f"[ERROR] Exception occurred: {str(e)}")
        print(f"[ERROR] Type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        print("=" * 80)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(is_success=False, message=str(e)).dict()
        )


@app.post("/extract-bill-data-json", response_model=SuccessResponse)
async def extract_bill_data_json(request: URLRequest):
    """
    Extract bill data from PDF or image URL using JSON body.
    
    **Example with curl:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data-json \
      -H "Content-Type: application/json" \
      -d '{"document_url": "https://example.com/bill.pdf"}'
    ```
    """
    return await extract_bill_data_internal(document_url=request.document_url, document_file=None)


@app.post("/extract-bill-data", response_model=SuccessResponse)
async def extract_bill_data(
    document_url: Optional[str] = Form(None, description="URL to PDF or image (http/https)"),
    document_file: Optional[UploadFile] = File(None, description="Upload PDF or image file directly")
):
    """
    Extract bill data from PDF or image (Form-data).
    
    **For URL input:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data \
      -F "document_url=https://example.com/bill.pdf"
    ```
    
    **For file upload:**
    ```bash
    curl -X POST http://localhost:8000/extract-bill-data \
      -F "document_file=@bill.pdf"
    ```
    
    **For JSON body (alternative):**
    Use `/extract-bill-data-json` endpoint instead.
    """
    return await extract_bill_data_internal(document_url=document_url, document_file=document_file)
