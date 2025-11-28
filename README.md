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

## Deployment

See `DEPLOYMENT.md` for deployment instructions.

