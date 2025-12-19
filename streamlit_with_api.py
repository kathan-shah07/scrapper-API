"""
Hybrid Streamlit + FastAPI app for Streamlit Cloud deployment
Exposes API endpoints through Streamlit URL for external workflows (n8n, HTTP triggers, etc.)

This file combines:
1. FastAPI server (runs in background thread) - for internal API access
2. Streamlit UI - for manual testing and interaction
3. API Proxy - allows API access through Streamlit URL query parameters

Main file to deploy on Streamlit Cloud.
"""

import streamlit as st
import requests
import json
import threading
import uvicorn
import time
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional
from urllib.parse import urlparse, parse_qs

from groww_scraper import GrowwScraper

# ==================== FastAPI Setup ====================
# FastAPI application for REST API endpoints
# This runs in a background thread to provide API access
api_app = FastAPI(
    title="Groww Mutual Fund Scraper API",
    description="REST API for scraping Groww mutual fund pages",
    version="1.0.0"
)

# Enable CORS (Cross-Origin Resource Sharing) to allow requests from any origin
# This is necessary for external workflows like n8n to access the API
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you may want to restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Default configuration for the scraper
# These settings control how the scraper behaves
DEFAULT_SCRAPER_CONFIG = {
    "output_dir": "data/mutual_funds",  # Directory to save JSON output files
    "use_interactive": True,  # Use Playwright/Selenium for dynamic content (recommended)
    "download_dir": "data/downloaded_html",  # Temporary directory for HTML downloads
    "download_first": False  # Whether to download HTML before scraping (slower but more reliable)
}

# Pydantic models for request/response validation
class ScrapeRequest(BaseModel):
    """Request model for POST /scrape endpoint"""
    url: HttpUrl  # Validated URL field
    use_interactive: Optional[bool] = True  # Optional: use browser automation
    download_first: Optional[bool] = False  # Optional: download HTML first

class ScrapeResponse(BaseModel):
    """Response model for all scraping endpoints"""
    success: bool  # Whether scraping was successful
    data: Optional[dict] = None  # Scraped fund data (if successful)
    error: Optional[str] = None  # Error message (if failed)
    message: Optional[str] = None  # Status message

# ==================== Shared Scraper Function ====================
def scrape_fund(url: str, use_interactive: bool = True, download_first: bool = False):
    """
    Shared scraping function used by both FastAPI endpoints and Streamlit UI.
    
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

# ==================== FastAPI Endpoints ====================
@api_app.get("/")
async def root():
    """Root endpoint - returns API information and available endpoints"""
    return {
        "name": "Groww Mutual Fund Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "GET /scrape": "Scrape a fund page (query parameter: url)",
            "POST /scrape": "Scrape a fund page (JSON body with url)",
            "GET /health": "Health check endpoint"
        }
    }

@api_app.get("/health")
async def health_check():
    """Health check endpoint - used to verify API is running"""
    return {"status": "healthy", "service": "groww-scraper-api"}

@api_app.get("/scrape", response_model=ScrapeResponse)
async def scrape_get(
    url: str = Query(..., description="URL of the Groww mutual fund page to scrape"),
    use_interactive: Optional[bool] = Query(None, description="Use interactive browser (Playwright/Selenium)"),
    download_first: Optional[bool] = Query(None, description="Download HTML first before scraping")
):
    """
    Scrape a Groww mutual fund page using GET request.
    
    This endpoint accepts URL and optional parameters as query parameters.
    Example: GET /scrape?url=https://groww.in/mutual-funds/...&use_interactive=true
    
    Args:
        url: URL of the mutual fund page to scrape (required)
        use_interactive: Whether to use browser automation (optional, default: True)
        download_first: Whether to download HTML first (optional, default: False)
        
    Returns:
        ScrapeResponse with success status and scraped data or error message
    """
    try:
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Perform scraping with provided or default settings
        data = scrape_fund(
            url,
            use_interactive if use_interactive is not None else DEFAULT_SCRAPER_CONFIG["use_interactive"],
            download_first if download_first is not None else DEFAULT_SCRAPER_CONFIG["download_first"]
        )
        
        # Return response based on scraping result
        if data is None:
            return ScrapeResponse(
                success=False,
                error="Failed to scrape the page",
                message="Scraping failed"
            )
        
        return ScrapeResponse(
            success=True,
            data=data,
            message="Scraping completed successfully"
        )
    except Exception as e:
        # Handle any errors during scraping
        return ScrapeResponse(
            success=False,
            error=str(e),
            message="An error occurred during scraping"
        )

@api_app.post("/scrape", response_model=ScrapeResponse)
async def scrape_post(request: ScrapeRequest):
    """
    Scrape a Groww mutual fund page using POST request.
    
    This endpoint accepts URL and optional parameters in JSON body.
    Example: POST /scrape with body {"url": "https://groww.in/mutual-funds/..."}
    
    Args:
        request: ScrapeRequest object containing URL and optional parameters
        
    Returns:
        ScrapeResponse with success status and scraped data or error message
    """
    try:
        url = str(request.url)
        # Perform scraping with provided or default settings
        data = scrape_fund(
            url,
            request.use_interactive if request.use_interactive is not None else DEFAULT_SCRAPER_CONFIG["use_interactive"],
            request.download_first if request.download_first is not None else DEFAULT_SCRAPER_CONFIG["download_first"]
        )
        if data is None:
            return ScrapeResponse(success=False, error="Failed to scrape", message="Scraping failed")
        return ScrapeResponse(success=True, data=data, message="Scraping completed successfully")
    except Exception as e:
        return ScrapeResponse(success=False, error=str(e), message="An error occurred")

# ==================== Start FastAPI Server ====================
def start_api_server():
    """
    Start FastAPI server in a background thread.
    
    This allows the API to run alongside the Streamlit app.
    The server runs on port 8000 (or PORT environment variable if set).
    """
    try:
        # Try to get port from environment (Streamlit Cloud may set this)
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(
            api_app,
            host="0.0.0.0",  # Listen on all interfaces
            port=port,
            log_level="warning"  # Reduce log verbosity
        )
    except Exception as e:
        print(f"API server error: {e}")

# Initialize API server in background thread (only once per session)
# This ensures the FastAPI server starts when Streamlit loads
if 'api_server_started' not in st.session_state:
    try:
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
        st.session_state.api_server_started = True
        time.sleep(2)  # Give server time to start before first request
    except Exception as e:
        st.session_state.api_server_started = False
        st.session_state.api_error = str(e)

# ==================== Streamlit API Proxy ====================
# This section allows API access through Streamlit URL query parameters
# This is essential for Streamlit Cloud deployment where only port 8501 is exposed

# Helper function to get query params (works with both old and new Streamlit APIs)
def get_query_param(key, default=None):
    """
    Get query parameter value, handling both old and new Streamlit APIs.
    
    Streamlit changed its query parameter API in version 1.28.0.
    This function provides backward compatibility.
    
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

# Check if this is an API request (via query parameter)
# Example: https://your-app.streamlit.app/?api=scrape&url=...
is_api_request = get_query_param("api") is not None
api_endpoint = get_query_param("api")

# Get Streamlit Cloud URL for API documentation
# This detects if running on Streamlit Cloud and constructs the appropriate base URL
streamlit_url = os.getenv("STREAMLIT_SERVER_ADDRESS", "localhost")
if "streamlit.app" in streamlit_url or "streamlit.io" in streamlit_url:
    # Running on Streamlit Cloud - use HTTPS
    base_url = f"https://{streamlit_url}" if not streamlit_url.startswith("http") else streamlit_url
else:
    # Running locally - use HTTP with port
    base_url = f"http://{streamlit_url}:8501"

# ==================== API Proxy Handler ====================
# Note: Streamlit always returns HTML, so for pure JSON API responses,
# use the FastAPI server on port 8000 instead: http://localhost:8000/scrape?url=...
# This section provides a UI-friendly JSON view for testing purposes.

if is_api_request:
    # This is an API request - show JSON in UI (for testing)
    # For production API calls, use FastAPI server on port 8000
    st.set_page_config(page_title="API", layout="centered")
    
    # Show notice about FastAPI server
    st.info("💡 **For pure JSON API responses, use the FastAPI server:** `http://localhost:8000/scrape?url=...`")
    
    if api_endpoint == "scrape":
        # Handle scrape endpoint via query parameters
        # Example: ?api=scrape&url=https://groww.in/mutual-funds/...
        url = get_query_param("url")
        use_interactive_str = get_query_param("use_interactive", "true")
        download_first_str = get_query_param("download_first", "false")
        
        # Convert string parameters to boolean
        use_interactive = use_interactive_str.lower() == "true" if isinstance(use_interactive_str, str) else True
        download_first = download_first_str.lower() == "true" if isinstance(download_first_str, str) else False
        
        if not url:
            # Missing required parameter
            st.error("Missing 'url' parameter")
            st.json({
                "success": False,
                "error": "Missing 'url' parameter",
                "message": "Invalid request"
            })
        else:
            try:
                # Show progress
                with st.spinner("Scraping fund data..."):
                    # Perform scraping
                    data = scrape_fund(url, use_interactive, download_first)
                
                if data:
                    # Return successful response with scraped data
                    st.success("✅ Scraping completed successfully!")
                    st.json({
                        "success": True,
                        "data": data,
                        "message": "Scraping completed successfully"
                    })
                else:
                    # Scraping failed
                    st.error("Failed to scrape the page")
                    st.json({
                        "success": False,
                        "error": "Failed to scrape the page",
                        "message": "Scraping failed"
                    })
            except Exception as e:
                # Handle errors
                st.error(f"Error: {str(e)}")
                st.json({
                    "success": False,
                    "error": str(e),
                    "message": "An error occurred during scraping"
                })
    
    elif api_endpoint == "health":
        # Health check endpoint
        st.success("✅ API is healthy")
        st.json({
            "status": "healthy",
            "service": "groww-scraper-api",
            "streamlit_url": base_url,
            "fastapi_url": "http://localhost:8000"
        })
    
    else:
        # Unknown endpoint - return API documentation
        st.json({
            "name": "Groww Mutual Fund Scraper API",
            "version": "1.0.0",
            "note": "For pure JSON responses, use FastAPI server on port 8000",
            "endpoints": {
                "FastAPI GET": "http://localhost:8000/scrape?url={url}",
                "FastAPI POST": "http://localhost:8000/scrape (with JSON body)",
                "FastAPI Health": "http://localhost:8000/health",
                "Streamlit UI": f"{base_url}/?api=scrape&url={{url}} (returns HTML with JSON)"
            },
            "api_base_url": base_url
        })
    
    # Stop here - don't render the UI for API requests
    st.stop()

# ==================== Streamlit UI ====================
# If not an API request, render the normal Streamlit UI for manual testing

# Configure Streamlit page
st.set_page_config(
    page_title="Groww Mutual Fund Scraper",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page header
st.title("📊 Groww Mutual Fund Scraper")
st.markdown("""
This tool scrapes mutual fund data from Groww pages and returns structured JSON data.
**REST API is available through this Streamlit URL for external workflows.**
""")

# Sidebar: API Information
# Display API base URL and endpoint examples
st.sidebar.header("🌐 API Information")
st.sidebar.markdown(f"""
**FastAPI Server (Pure JSON):**  
`http://localhost:8000`

**FastAPI Endpoints:**
- **GET**: `http://localhost:8000/scrape?url=https://groww.in/mutual-funds/...`
- **POST**: `http://localhost:8000/scrape` (with JSON body)
- **Health**: `http://localhost:8000/health`

**Streamlit UI (HTML with JSON):**  
`{base_url}`

**Streamlit Endpoints (for testing):**
- **GET**: `{base_url}/?api=scrape&url=https://groww.in/mutual-funds/...`
- **Health**: `{base_url}/?api=health`

**Note:** For API integrations (n8n, etc.), use the FastAPI server on port 8000 for pure JSON responses.
""")

# Sidebar: API Server Status
# Check if internal FastAPI server is running
st.sidebar.header("API Server Status")
try:
    # Try to check internal API server (runs on port 8000)
    internal_api_url = "http://localhost:8000"
    health_response = requests.get(f"{internal_api_url}/health", timeout=2)
    if health_response.status_code == 200:
        st.sidebar.success("✅ Internal API: Online (port 8000)")
        st.sidebar.info("💡 Use Streamlit URL for external access")
    else:
        st.sidebar.warning("⚠️ Internal API: Unknown status")
except:
    # Internal API not accessible (normal for Streamlit Cloud)
    st.sidebar.info("ℹ️ Internal API: Not accessible (using Streamlit proxy)")

# Main UI: Scraping Interface
st.header("Scrape Fund Data")

# URL input field
url = st.text_input(
    "Enter Groww Mutual Fund URL",
    placeholder="https://groww.in/mutual-funds/...",
    help="Paste the URL of the mutual fund page you want to scrape"
)

# Advanced options (collapsible)
with st.expander("Advanced Options"):
    use_interactive = st.checkbox("Use Interactive Browser", value=True, 
                                   help="Use Playwright/Selenium for dynamic content (recommended)")
    download_first = st.checkbox("Download HTML First", value=False, 
                                  help="Download HTML before scraping (slower but more reliable)")

# Scrape button
if st.button("🚀 Scrape Fund Data", type="primary", use_container_width=True):
    # Validate input
    if not url:
        st.error("Please enter a URL")
        st.stop()
    
    if not url.startswith(('http://', 'https://')):
        st.error("Invalid URL format")
        st.stop()
    
    # Show progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Scraping fund data...")
        progress_bar.progress(30)
        
        # Perform scraping
        data = scrape_fund(url, use_interactive, download_first)
        progress_bar.progress(90)
        
        if data:
            # Success - display results
            progress_bar.progress(100)
            status_text.success("✅ Scraping completed successfully!")
            
            st.header("📋 Scraped Data")
            st.json(data)  # Display JSON in formatted view
            
            # Download button for JSON file
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"fund_data_{int(time.time())}.json",
                mime="application/json"
            )
        else:
            # Scraping failed
            st.error("❌ Failed to scrape the page")
    except Exception as e:
        # Handle errors
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
    finally:
        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()

# API Documentation Section
# Expandable section with examples for external workflows
with st.expander("📖 API Usage for External Workflows"):
    st.markdown(f"""
    ### Using with n8n, HTTP triggers, or other workflows:
    
    **⚠️ Important:** For pure JSON API responses, use the FastAPI server on port 8000, not the Streamlit URL.
    
    **FastAPI GET Request (Recommended for APIs):**
    ```bash
    curl "http://localhost:8000/scrape?url=https://groww.in/mutual-funds/..."
    ```
    
    **FastAPI POST Request:**
    ```bash
    curl -X POST "http://localhost:8000/scrape" \\
         -H "Content-Type: application/json" \\
         -d '{{"url": "https://groww.in/mutual-funds/..."}}'
    ```
    
    **With Python:**
    ```python
    import requests
    
    # Use FastAPI server for pure JSON
    response = requests.get(
        "http://localhost:8000/scrape",
        params={{"url": "https://groww.in/mutual-funds/..."}}
    )
    
    data = response.json()
    if data["success"]:
        fund_data = data["data"]
    ```
    
    **With n8n HTTP Request Node:**
    1. Method: GET
    2. URL: `http://localhost:8000/scrape`
    3. Query Parameters:
       - `url`: `{{ $json.url }}`
    
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
    curl "http://localhost:8000/health"
    ```
    
    **Note:** The Streamlit URL (`{base_url}/?api=scrape&url=...`) returns HTML with embedded JSON, which is fine for browser testing but not ideal for API integrations.
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Groww Mutual Fund Scraper | API accessible via Streamlit URL</p>
</div>
""", unsafe_allow_html=True)
