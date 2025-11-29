# Using ngrok to Expose Localhost API

This guide explains how to expose your local FastAPI server using ngrok, making it accessible via a public URL.

## Why Use ngrok?

- Test your API from external services or mobile devices
- Share your local development API with others
- Test webhooks that need to call your API
- Access your API from anywhere during development

## Prerequisites

1. **Install ngrok**:
   - Download from: https://ngrok.com/download
   - Or install via package manager:
     - **Windows (Chocolatey)**: `choco install ngrok`
     - **Windows (Scoop)**: `scoop install ngrok`
     - **Mac**: `brew install ngrok`
     - **Linux**: `sudo snap install ngrok`

2. **Create ngrok account** (optional but recommended):
   - Sign up at: https://dashboard.ngrok.com/signup
   - Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

## Setup Instructions

### Step 1: Authenticate ngrok (First time only)

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### Step 2: Start Your FastAPI Server

In one terminal, start your API:

```bash
# Windows PowerShell/Command Prompt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Or if using virtual environment
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Your API will be running at: `http://127.0.0.1:8000` or `http://localhost:8000`

### Step 3: Start ngrok Tunnel

In a **second terminal**, start ngrok:

```bash
# Basic command
ngrok http 8000

# With custom subdomain (requires paid plan)
ngrok http 8000 --subdomain=your-subdomain

# With authentication (protect your API)
ngrok http 8000 --basic-auth="username:password"
```

### Step 4: Access Your API

After starting ngrok, you'll see output like:

```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:8000
```

Use the `https://` URL to access your API from anywhere!

## Quick Start Script

Create a file `start_with_ngrok.bat` (Windows) or `start_with_ngrok.sh` (Linux/Mac):

### Windows (`start_with_ngrok.bat`):

```batch
@echo off
echo Starting FastAPI server...
start "FastAPI Server" cmd /k "uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak
echo Starting ngrok tunnel...
start "ngrok Tunnel" cmd /k "ngrok http 8000"
echo.
echo FastAPI Server: http://localhost:8000
echo Check ngrok window for public URL
pause
```

### Linux/Mac (`start_with_ngrok.sh`):

```bash
#!/bin/bash
echo "Starting FastAPI server..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
FASTAPI_PID=$!

sleep 3
echo "Starting ngrok tunnel..."
ngrok http 8000 &
NGROK_PID=$!

echo ""
echo "FastAPI Server: http://localhost:8000"
echo "Check ngrok output for public URL"
echo "Press Ctrl+C to stop both services"

wait
```

## Testing Your ngrok URL

Once ngrok is running, test these endpoints:

1. **Root (Form Interface)**:
   ```
   https://your-ngrok-url.ngrok-free.app/
   ```

2. **Health Check**:
   ```
   https://your-ngrok-url.ngrok-free.app/health
   ```

3. **API Docs**:
   ```
   https://your-ngrok-url.ngrok-free.app/docs
   ```

4. **Extract Bill Data**:
   ```bash
   curl -X POST https://your-ngrok-url.ngrok-free.app/extract-bill-data \
     -F "document_url=https://example.com/bill.pdf"
   ```

## ngrok Features

### Free Tier:
- ✅ Public HTTPS URL
- ✅ Up to 40 connections/minute
- ✅ Random subdomain each time
- ✅ ngrok inspection UI (http://127.0.0.1:4040)

### Paid Plans Include:
- ✅ Static domain (same URL every time)
- ✅ Custom subdomain
- ✅ More connections
- ✅ Reserved IP addresses
- ✅ Authentication options

## Troubleshooting

### Issue: "ngrok: command not found"
**Solution**: Add ngrok to your PATH or use full path to executable

### Issue: "ERR_NGROK_108 - Your account is limited"
**Solution**: Sign up for a free ngrok account and add your auth token

### Issue: "Address already in use"
**Solution**: Make sure port 8000 is not already in use, or change the port:
```bash
uvicorn app.main:app --port 8080
ngrok http 8080
```

### Issue: "Tunnel not responding"
**Solution**: 
1. Verify FastAPI is running on the correct port
2. Check firewall settings
3. Ensure ngrok is pointing to the correct port

## Security Notes

⚠️ **Important**: When using ngrok, your local API is exposed to the internet!

1. **For Development Only**: Only use ngrok for testing, not production
2. **Use Authentication**: Add basic auth to protect your API:
   ```bash
   ngrok http 8000 --basic-auth="username:password"
   ```
3. **Monitor Access**: Check ngrok's web interface at http://127.0.0.1:4040
4. **Don't Share URLs**: Keep your ngrok URL private unless you want others to access it

## Alternative: Cloudflare Tunnel

If you prefer an alternative to ngrok, you can use Cloudflare Tunnel (cloudflared):

```bash
# Install cloudflared
# Then run:
cloudflared tunnel --url http://localhost:8000
```

## Next Steps

- Set up environment variables for local development
- Test your API from external services
- Share your ngrok URL with team members for testing
- Monitor requests via ngrok's web interface

