# Bill Extraction API

FastAPI service for extracting bill items from PDF and image documents using Google Gemini AI.

## Features

- Extract bill line items from PDF files
- Extract bill line items from image files  
- Support for PDF URLs and Image URLs
- Support for local file uploads
- Multi-page PDF processing
- JSON output format

## API Endpoints

- `POST /extract-bill-data` - Main endpoint (supports URL or file upload)
- `POST /extract-bill-data-url` - Legacy endpoint (URL only)
- `GET /docs` - API documentation

## Environment Variables

- `GEMINI_API_KEY` - Required. Your Google Gemini API key.

## Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Your API will be available at: `http://localhost:8000`

### Expose Localhost with ngrok

To make your local API accessible from the internet (for testing):

1. **Install ngrok**: Download from https://ngrok.com/download
2. **Run the startup script**:
   - Windows: `start_with_ngrok.bat`
   - Linux/Mac: `chmod +x start_with_ngrok.sh && ./start_with_ngrok.sh`
3. **Or manually**:
   ```bash
   # Terminal 1: Start FastAPI
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   
   # Terminal 2: Start ngrok
   ngrok http 8000
   ```

See `NGROK_SETUP.md` for detailed ngrok setup instructions.

## Deployment

See `DEPLOYMENT.md` for deployment instructions.

