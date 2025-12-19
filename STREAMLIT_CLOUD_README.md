# Streamlit Cloud Deployment Guide

## Quick Start

1. **Deploy `streamlit_cloud.py`** on Streamlit Cloud (set as main file)
2. **Use `parse_streamlit_json.py`** helper to get FastAPI-like behavior
3. Your API works exactly like the local FastAPI server!

## The Problem

Streamlit Cloud always returns HTML, not pure JSON like FastAPI. This makes it difficult to use in API integrations.

## The Solution

The `parse_streamlit_json.py` helper extracts JSON from HTML, giving you the **exact same behavior** as FastAPI.

## Usage

### Method 1: Use the Helper Function (Recommended)

```python
from parse_streamlit_json import call_streamlit_api

# Works exactly like FastAPI!
result = call_streamlit_api(
    "https://your-app.streamlit.app",
    "https://groww.in/mutual-funds/..."
)

if result and result.get("success"):
    fund_data = result["data"]
    print(fund_data)
```

### Method 2: Manual Parsing

```python
import requests
from parse_streamlit_json import parse_streamlit_json_response

response = requests.get(
    "https://your-app.streamlit.app",
    params={
        "api": "scrape",
        "url": "https://groww.in/mutual-funds/..."
    }
)

data = parse_streamlit_json_response(response.text)
if data and data.get("success"):
    fund_data = data["data"]
```

## API Endpoints

**Scrape:**
```
https://your-app.streamlit.app/?api=scrape&url=https://groww.in/mutual-funds/...
```

**Health Check:**
```
https://your-app.streamlit.app/?api=health
```

**API Docs:**
```
https://your-app.streamlit.app/?api=docs
```

## Response Format

Same as FastAPI:
```json
{
  "success": true,
  "data": { ... },
  "message": "Scraping completed successfully"
}
```

## n8n Integration

1. Add **HTTP Request** node
2. Method: GET
3. URL: `https://your-app.streamlit.app/`
4. Query Parameters:
   - `api`: `scrape`
   - `url`: `{{ $json.url }}`
5. Add **Code** node to parse JSON:
   ```javascript
   const html = $input.item.json.body;
   const jsonMatch = html.match(/<script[^>]*id=["']api-response["'][^>]*>(.*?)<\/script>/s);
   if (jsonMatch) {
     return JSON.parse(jsonMatch[1]);
   }
   ```

## Key Differences from Local

| Feature | Local (FastAPI) | Streamlit Cloud |
|---------|----------------|-----------------|
| Response Format | Pure JSON | HTML with JSON |
| Parsing | Direct `response.json()` | Use `parse_streamlit_json.py` |
| Interface | Same | Same (with helper) |
| URL | `http://localhost:8000/scrape?url=...` | `https://app.streamlit.app/?api=scrape&url=...` |

## Benefits

✅ **Same interface** as FastAPI (with helper)
✅ **Same response format**
✅ **Works with n8n, HTTP triggers, etc.**
✅ **No code changes needed** (just use the helper)

