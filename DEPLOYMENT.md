# Deployment to Render

This guide explains how to deploy the Bill Extraction API to Render.

## Prerequisites

1. GitHub account (for connecting your repository)
2. Render account (sign up at https://render.com)
3. Gemini API Key

## Files Required for Deployment

The following files are already created for you:

- ✅ `Procfile` - Tells Render how to run your app
- ✅ `requirements.txt` - Python dependencies
- ✅ `runtime.txt` - Python version specification
- ✅ `render.yaml` - Optional Render configuration (for Infrastructure as Code)
- ✅ `app/__init__.py` - Makes app a Python package
- ✅ `.gitignore` - Excludes unnecessary files from git

## Deployment Steps

### Option 1: Deploy via Render Dashboard (Recommended)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Connect Repository to Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository

3. **Configure the Service**
   - **Name**: `bill-extraction-api` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Set Environment Variables**
   - Go to "Environment" tab
   - Add environment variable:
     - **Key**: `GEMINI_API_KEY`
     - **Value**: Your Gemini API key (e.g., `AIzaSyA-Joy5PifPUbeb12wP2_tbYSSnwKpeyPg`)

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app

### Option 2: Deploy via render.yaml (Infrastructure as Code)

1. **Push code to GitHub** (same as above)

2. **Create Blueprint**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and use it

3. **Update Environment Variables**
   - After deployment, go to your service
   - Add `GEMINI_API_KEY` environment variable in the dashboard

## Environment Variables

Required environment variable:
- `GEMINI_API_KEY` - Your Google Gemini API key

Optional (already handled by code):
- `GOOGLE_API_KEY` - Alternative name (code checks both)

## Post-Deployment

After deployment, your API will be available at:
- Production URL: `https://your-service-name.onrender.com`

### Test the Deployment

1. **Health Check** (FastAPI docs):
   ```
   https://your-service-name.onrender.com/docs
   ```

2. **Test Endpoint** (using curl):
   ```bash
   curl -X POST "https://your-service-name.onrender.com/extract-bill-data" \
     -F "document_file=@bill.pdf"
   ```

## Important Notes

1. **Free Tier Limitations**:
   - Services spin down after 15 minutes of inactivity
   - First request after spin-down may take 30-60 seconds
   - Consider upgrading to paid tier for production

2. **File Size Limits**:
   - Free tier has upload size limits
   - Consider using URLs instead of file uploads for large files

3. **API Key Security**:
   - Never commit API keys to git
   - Always use environment variables
   - The `.gitignore` file excludes `.env` files

4. **Dependencies**:
   - All dependencies are in `requirements.txt`
   - Render automatically installs them during build

## Troubleshooting

### Build Fails
- Check that all dependencies are in `requirements.txt`
- Verify Python version in `runtime.txt` matches Render's support

### Service Won't Start
- Check logs in Render dashboard
- Verify `Procfile` command is correct
- Ensure `GEMINI_API_KEY` is set

### Timeout Issues
- Free tier has timeout limits
- Large PDFs may take longer to process
- Consider increasing timeout in Render settings

### Missing Dependencies
- Verify `pymupdf` is in requirements (not `pdf2image`)
- Check that all imports in code have corresponding packages

## File Structure for Deployment

```
baja/
├── app/
│   ├── __init__.py          # ✅ Package marker
│   ├── main.py              # ✅ FastAPI app
│   ├── llm_client.py        # ✅ Gemini integration
│   ├── ocr_pipeline.py      # ✅ PDF/image processing
│   ├── schemas.py           # ✅ Data models
│   └── test.py              # ❌ Not needed in production
├── requirements.txt         # ✅ Dependencies
├── Procfile                # ✅ Render start command
├── runtime.txt             # ✅ Python version
├── render.yaml             # ✅ Optional config
├── .gitignore              # ✅ Git exclusions
└── DEPLOYMENT.md           # 📖 This file
```

## Support

For issues:
1. Check Render logs: Dashboard → Your Service → Logs
2. Test locally first: `python -m app.test train_sample_1.pdf`
3. Verify environment variables are set correctly

