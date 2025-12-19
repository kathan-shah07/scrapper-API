# Groww Mutual Fund Scraper - REST API & Streamlit UI

A comprehensive scraper for Groww mutual fund pages with both REST API and Streamlit UI interfaces, designed for Streamlit Cloud deployment.

## Features

- 📊 Scrapes comprehensive mutual fund data from Groww pages
- 🔌 REST API endpoint accessible via Streamlit URL (compatible with n8n, HTTP triggers, etc.)
- 🖥️ Streamlit UI for manual testing and interaction
- 🤖 Supports Playwright and Selenium for dynamic content
- 📁 Structured JSON output
- ☁️ Optimized for Streamlit Cloud deployment

## Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers (Optional but Recommended)

```bash
playwright install chromium
```

### 3. Run Locally

```bash
streamlit run streamlit_with_api.py
```

The app will be available at `http://localhost:8501`

## Deployment to Streamlit Cloud

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Deploy Groww Scraper"
git push origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repository
3. Set the main file to: **`streamlit_cloud.py`** (use this for Streamlit Cloud)
4. Deploy!

**Important:** 
- Use `streamlit_cloud.py` for Streamlit Cloud deployment
- Streamlit Cloud returns HTML with embedded JSON (not pure JSON like FastAPI)
- Use the `parse_streamlit_json.py` helper to extract JSON and get the same behavior as FastAPI
- The helper function `call_streamlit_api()` provides the exact same interface as calling FastAPI

### Step 3: Access Your API

Once deployed, your API will be accessible via your Streamlit Cloud URL:

```
https://your-app-name.streamlit.app/?api=scrape&url=https://groww.in/mutual-funds/...
```

**Getting FastAPI-like Behavior on Streamlit Cloud:**

Since Streamlit Cloud returns HTML with embedded JSON, use the `parse_streamlit_json.py` helper to get the exact same behavior as FastAPI:

```python
from parse_streamlit_json import call_streamlit_api

# This works exactly like calling FastAPI!
result = call_streamlit_api(
    "https://your-app.streamlit.app",
    "https://groww.in/mutual-funds/..."
)

if result and result.get("success"):
    fund_data = result["data"]  # Same format as FastAPI response
```

The `call_streamlit_api()` function provides the **exact same interface** as FastAPI, so your code works identically!

## API Usage

### ⚠️ Important: Use FastAPI Server for Pure JSON Responses

**For API integrations (n8n, HTTP triggers, etc.), use the FastAPI server on port 8000**, not the Streamlit URL. The Streamlit URL returns HTML with embedded JSON, which is fine for browser testing but not ideal for API integrations.

### FastAPI Server Endpoints (Pure JSON)

**Local Development:**
- **Scrape (GET)**: `http://localhost:8000/scrape?url=https://groww.in/mutual-funds/...`
- **Scrape (POST)**: `http://localhost:8000/scrape` (with JSON body)
- **Health Check**: `http://localhost:8000/health`

**Streamlit Cloud Deployment:**
- The FastAPI server runs in the background but may not be accessible externally
- For Streamlit Cloud, use the Streamlit URL for testing (returns HTML with JSON)
- For production API, consider deploying FastAPI separately

### API Response Format

```json
{
  "success": true,
  "data": {
    "fund_name": "...",
    "nav": {...},
    "returns": {...},
    "aum": "...",
    "summary": {...},
    "cost_and_tax": {...},
    "portfolio": {...},
    ...
  },
  "message": "Scraping completed successfully"
}
```

### Using with Python

```python
import requests

# Use FastAPI server for pure JSON (recommended for APIs)
response = requests.get(
    "http://localhost:8000/scrape",  # Use port 8000 for FastAPI
    params={
        "url": "https://groww.in/mutual-funds/..."
    }
)

data = response.json()
if data["success"]:
    fund_data = data["data"]
    print(fund_data)
```

**Note:** For Streamlit Cloud deployment, the FastAPI server may not be accessible. In that case, parse the JSON from the HTML response or use the Streamlit URL for testing purposes.

### Integration with n8n

**For Local Development:**
1. Add an **HTTP Request** node in your n8n workflow
2. Configure:
   - **Method**: GET
   - **URL**: `http://localhost:8000/scrape` (FastAPI server)
   - **Query Parameters**:
     - `url`: `{{ $json.url }}`
3. The response will contain:
   - `success`: boolean indicating success/failure
   - `data`: scraped fund data (if successful)
   - `error`: error message (if failed)
   - `message`: status message

**For Streamlit Cloud:**
- The FastAPI server may not be accessible externally
- You may need to parse JSON from HTML response or deploy FastAPI separately

### Using with cURL

```bash
# Scrape a fund
curl "https://your-app.streamlit.app/?api=scrape&url=https://groww.in/mutual-funds/..."

# Health check
curl "https://your-app.streamlit.app/?api=health"
```

## Local Development

### Run Streamlit App

```bash
streamlit run streamlit_with_api.py
```

The app includes:
- **UI**: Manual scraping interface at `http://localhost:8501`
- **API**: Accessible via `http://localhost:8501/?api=scrape&url=...`

### Direct Python Usage

```python
from groww_scraper import GrowwScraper

scraper = GrowwScraper()
data = scraper.parse_fund_data("https://groww.in/mutual-funds/...")
print(data)
```

## File Structure

```
.
├── groww_scraper.py          # Core scraper class (required)
├── streamlit_with_api.py    # Main app file for Streamlit Cloud (required)
├── requirements.txt          # Python dependencies (required)
├── README.md                 # This file
└── .streamlit/
    └── config.toml          # Streamlit configuration (optional)
```

## Configuration

The scraper supports several configuration options in `streamlit_with_api.py`:

- `use_interactive`: Use Playwright/Selenium for dynamic content (default: True)
- `download_first`: Download HTML before scraping (default: False)
- `output_dir`: Directory for saving JSON files (default: "data/mutual_funds")
- `download_dir`: Directory for temporary HTML files (default: "data/downloaded_html")

## Troubleshooting

### Playwright Installation Issues

If Playwright fails to install:
```bash
playwright install chromium
playwright install-deps chromium
```

### Selenium Issues

If Selenium fails, ensure ChromeDriver is installed:
```bash
pip install chromedriver-autoinstaller
```

### API Not Responding on Streamlit Cloud

- Check that you're using the correct query parameter format: `?api=scrape&url=...`
- Verify the Streamlit app is running and accessible
- Check Streamlit Cloud logs for errors

### Scraping Fails

- Ensure Playwright/Selenium dependencies are installed
- Check that the target URL is accessible
- Review error messages in the API response
- Try setting `use_interactive=True` for dynamic content

### Timeout Issues

- Streamlit Cloud has execution time limits
- Consider optimizing the scraper for faster execution
- Use `download_first=False` to speed up scraping

## API Query Parameters

### Scrape Endpoint

- `api` (required): Set to `"scrape"`
- `url` (required): URL of the Groww mutual fund page
- `use_interactive` (optional): `"true"` or `"false"` (default: `"true"`)
- `download_first` (optional): `"true"` or `"false"` (default: `"false"`)

### Health Check

- `api` (required): Set to `"health"`

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions, please check the code comments in `streamlit_with_api.py` and `groww_scraper.py` for detailed implementation notes.
