"""
Streamlit Cloud Deployment Version
Optimized for Streamlit Cloud - provides FastAPI-like JSON responses
Uses Streamlit's capabilities to return parseable JSON for API clients
"""

import streamlit as st
import json
import os
import time
from typing import Optional, Dict, Any

from groww_scraper import GrowwScraper

# ==================== Configuration ====================
DEFAULT_SCRAPER_CONFIG = {
    "output_dir": "data/mutual_funds",
    "use_interactive": True,
    "download_dir": "data/downloaded_html",
    "download_first": False
}

# ==================== Helper Functions ====================
def get_query_param(key, default=None):
    """
    Get query parameter value, handling both old and new Streamlit APIs.
    
    Args:
        key: Query parameter key to retrieve
        default: Default value if parameter is not found
        
    Returns:
        Query parameter value or default
    """
    try:
        # Try new API first (Streamlit >= 1.28.0)
        params = st.query_params
        if hasattr(params, 'get'):
            value = params.get(key, default)
            # New API returns single value or list
            return value[0] if isinstance(value, list) and len(value) > 0 else value
        else:
            return default
    except AttributeError:
        # Fallback to experimental API for older versions
        try:
            params = st.experimental_get_query_params()
            value = params.get(key, [default])
            return value[0] if isinstance(value, list) and len(value) > 0 else default
        except:
            return default

def scrape_fund(url: str, use_interactive: bool = True, download_first: bool = False) -> Optional[Dict[str, Any]]:
    """
    Shared scraping function used by both API and UI.
    
    Args:
        url: URL of the Groww mutual fund page to scrape
        use_interactive: Whether to use Playwright/Selenium for dynamic content
        download_first: Whether to download HTML before scraping
        
    Returns:
        Dictionary with scraped fund data, or None if scraping failed
    """
    scraper = GrowwScraper(
        output_dir=DEFAULT_SCRAPER_CONFIG["output_dir"],
        use_interactive=use_interactive,
        download_dir=DEFAULT_SCRAPER_CONFIG["download_dir"],
        download_first=download_first
    )
    return scraper.parse_fund_data(url)

def return_json_response(data: Dict[str, Any], status_code: int = 200):
    """
    Return JSON response in a way that's easily parseable from HTML.
    Uses multiple methods to embed JSON for maximum compatibility.
    
    Args:
        data: Dictionary to return as JSON
        status_code: HTTP status code (for reference)
    """
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Hide all Streamlit UI elements
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {padding: 0; margin: 0;}
    .stApp > header {display: none;}
    .stApp > div:first-child {padding-top: 0;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Method 1: JSON in script tag (easiest to parse)
    st.markdown(
        f'<script type="application/json" id="api-response">{json_str}</script>',
        unsafe_allow_html=True
    )
    
    # Method 2: JSON in pre tag (Streamlit's native JSON display)
    st.json(data)
    
    # Method 3: JSON as plain text in a hidden div (backup)
    st.markdown(
        f'<div id="api-json-data" style="display:none;">{json_str}</div>',
        unsafe_allow_html=True
    )
    
    # Method 4: Add metadata for easy extraction
    st.markdown(
        f'<meta name="api-status" content="{status_code}">',
        unsafe_allow_html=True
    )

# ==================== Get Query Parameters ====================
# Check if this is an API request (via query parameter)
is_api_request = get_query_param("api") is not None
api_endpoint = get_query_param("api")

# Get Streamlit Cloud URL
streamlit_url = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")
if "streamlit.app" in streamlit_url or "streamlit.io" in streamlit_url:
    base_url = f"https://{streamlit_url}" if not streamlit_url.startswith("http") else streamlit_url
else:
    base_url = f"http://{streamlit_url}:8501"

# ==================== API Handler ====================
if is_api_request:
    # This is an API request - return JSON response
    st.set_page_config(page_title="API", layout="centered")
    
    if api_endpoint == "scrape":
        # Handle scrape endpoint
        url = get_query_param("url")
        use_interactive_str = get_query_param("use_interactive", "true")
        download_first_str = get_query_param("download_first", "false")
        
        # Convert string parameters to boolean
        use_interactive = use_interactive_str.lower() == "true" if isinstance(use_interactive_str, str) else True
        download_first = download_first_str.lower() == "true" if isinstance(download_first_str, str) else False
        
        if not url:
            response_data = {
                "success": False,
                "error": "Missing 'url' parameter",
                "message": "Invalid request"
            }
            return_json_response(response_data, 400)
        else:
            try:
                # Perform scraping
                data = scrape_fund(url, use_interactive, download_first)
                
                if data:
                    response_data = {
                        "success": True,
                        "data": data,
                        "message": "Scraping completed successfully"
                    }
                    return_json_response(response_data, 200)
                else:
                    response_data = {
                        "success": False,
                        "error": "Failed to scrape the page",
                        "message": "Scraping failed"
                    }
                    return_json_response(response_data, 500)
            except Exception as e:
                response_data = {
                    "success": False,
                    "error": str(e),
                    "message": "An error occurred during scraping"
                }
                return_json_response(response_data, 500)
    
    elif api_endpoint == "health":
        response_data = {
            "status": "healthy",
            "service": "groww-scraper-api",
            "streamlit_url": base_url
        }
        return_json_response(response_data, 200)
    
    elif api_endpoint == "docs" or api_endpoint == "":
        response_data = {
            "name": "Groww Mutual Fund Scraper API",
            "version": "1.0.0",
            "endpoints": {
                "GET /?api=scrape&url={url}": "Scrape a fund page",
                "GET /?api=health": "Health check",
                "GET /?api=docs": "API documentation"
            },
            "api_base_url": base_url,
            "note": "JSON is embedded in HTML. Use parse_streamlit_json.py helper to extract JSON."
        }
        return_json_response(response_data, 200)
    
    else:
        response_data = {
            "success": False,
            "error": f"Unknown endpoint: {api_endpoint}",
            "message": "Invalid API endpoint",
            "available_endpoints": ["scrape", "health", "docs"]
        }
        return_json_response(response_data, 404)
    
    st.stop()

# ==================== Streamlit UI ====================
# If not an API request, render the normal Streamlit UI

st.set_page_config(
    page_title="Groww Mutual Fund Scraper",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Groww Mutual Fund Scraper")
st.markdown("""
This tool scrapes mutual fund data from Groww pages and returns structured JSON data.
**API is available through query parameters for external workflows.**
""")

# Sidebar: API Information
st.sidebar.header("🌐 API Information")
st.sidebar.markdown(f"""
**API Base URL:**  
`{base_url}`

**Available Endpoints:**

**Scrape:**
```
{base_url}/?api=scrape&url=https://groww.in/mutual-funds/...
```

**Health Check:**
```
{base_url}/?api=health
```

**API Docs:**
```
{base_url}/?api=docs
```

**Note:** Use `parse_streamlit_json.py` helper to extract JSON from HTML responses.
""")

# Main UI
st.header("Scrape Fund Data")

url = st.text_input(
    "Enter Groww Mutual Fund URL",
    placeholder="https://groww.in/mutual-funds/...",
    help="Paste the URL of the mutual fund page you want to scrape"
)

with st.expander("Advanced Options"):
    use_interactive = st.checkbox("Use Interactive Browser", value=True)
    download_first = st.checkbox("Download HTML First", value=False)

if st.button("🚀 Scrape Fund Data", type="primary", use_container_width=True):
    if not url:
        st.error("Please enter a URL")
        st.stop()
    
    if not url.startswith(('http://', 'https://')):
        st.error("Invalid URL format")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Scraping fund data...")
        progress_bar.progress(30)
        
        data = scrape_fund(url, use_interactive, download_first)
        progress_bar.progress(90)
        
        if data:
            progress_bar.progress(100)
            status_text.success("✅ Scraping completed successfully!")
            
            st.header("📋 Scraped Data")
            st.json(data)
            
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"fund_data_{int(time.time())}.json",
                mime="application/json"
            )
        else:
            st.error("❌ Failed to scrape the page")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
    finally:
        progress_bar.empty()
        status_text.empty()

# API Documentation
with st.expander("📖 API Usage for External Workflows"):
    st.markdown(f"""
    ### Using with n8n, HTTP triggers, or other workflows:
    
    **GET Request:**
    ```bash
    curl "{base_url}/?api=scrape&url=https://groww.in/mutual-funds/..."
    ```
    
    **With Python (using helper):**
    ```python
    from parse_streamlit_json import call_streamlit_api
    
    result = call_streamlit_api(
        "{base_url}",
        "https://groww.in/mutual-funds/..."
    )
    
    if result and result.get("success"):
        fund_data = result["data"]
    ```
    
    **With Python (manual parsing):**
    ```python
    import requests
    from parse_streamlit_json import parse_streamlit_json_response
    
    response = requests.get(
        "{base_url}/",
        params={{
            "api": "scrape",
            "url": "https://groww.in/mutual-funds/..."
        }}
    )
    
    data = parse_streamlit_json_response(response.text)
    if data and data.get("success"):
        fund_data = data["data"]
    ```
    
    **With n8n HTTP Request Node:**
    1. Method: GET
    2. URL: `{base_url}/`
    3. Query Parameters:
       - `api`: `scrape`
       - `url`: `{{ $json.url }}`
    4. Add a "Parse HTML" or "Extract JSON" step to get JSON from response
    
    **Response Format:**
    ```json
    {{
        "success": true,
        "data": {{ ... }},
        "message": "Scraping completed successfully"
    }}
    ```
    
    **Health Check:**
    ```bash
    curl "{base_url}/?api=health"
    ```
    """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Groww Mutual Fund Scraper | Streamlit Cloud Deployment</p>
</div>
""", unsafe_allow_html=True)
