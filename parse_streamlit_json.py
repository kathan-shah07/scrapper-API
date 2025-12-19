"""
Helper utility to parse JSON from Streamlit Cloud HTML responses
Use this when calling the Streamlit Cloud API endpoint to get the same behavior as FastAPI
"""

import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, Any, Optional
import re


def parse_streamlit_json_response(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON from Streamlit HTML response.
    
    Streamlit embeds JSON in HTML. This function extracts it using multiple methods
    to ensure compatibility with the FastAPI-like response format.
    
    Args:
        html_content: HTML response from Streamlit Cloud
        
    Returns:
        Parsed JSON data or None if not found
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: Try to extract from script tag with id="api-response" (most reliable)
    script_tag = soup.find('script', id='api-response')
    if script_tag and script_tag.string:
        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError:
            pass
    
    # Method 2: Extract from script tag with type="application/json"
    script_tags = soup.find_all('script', type='application/json')
    for script_tag in script_tags:
        if script_tag.string:
            try:
                return json.loads(script_tag.string)
            except json.JSONDecodeError:
                continue
    
    # Method 3: Extract from pre tag (Streamlit's JSON display)
    # Look for the pre tag that contains JSON (usually the first one with valid JSON)
    pre_tags = soup.find_all('pre')
    for pre_tag in pre_tags:
        text = pre_tag.get_text(strip=True)
        # Check if it looks like JSON
        if (text.startswith('{') or text.startswith('[')) and len(text) > 10:
            try:
                parsed = json.loads(text)
                # Validate it's our API response format
                if isinstance(parsed, dict) and ('success' in parsed or 'status' in parsed or 'name' in parsed):
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Method 4: Extract from hidden div with id="api-json-data"
    hidden_div = soup.find('div', id='api-json-data')
    if hidden_div and hidden_div.string:
        try:
            return json.loads(hidden_div.string)
        except json.JSONDecodeError:
            pass
    
    # Method 5: Try regex to find JSON in script tags
    script_pattern = r'<script[^>]*id=["\']api-response["\'][^>]*>(.*?)</script>'
    match = re.search(script_pattern, html_content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Method 6: Find any JSON-like structure in the HTML
    json_pattern = r'\{[^{}]*"success"[^{}]*\}'
    matches = re.findall(json_pattern, html_content, re.DOTALL)
    for match in matches:
        try:
            # Try to expand to full JSON object
            # Find the complete JSON by looking for balanced braces
            start = html_content.find(match)
            if start >= 0:
                brace_count = 0
                json_start = start
                for i, char in enumerate(html_content[start:], start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = html_content[json_start:i+1]
                            try:
                                return json.loads(json_str)
                            except json.JSONDecodeError:
                                break
        except:
            continue
    
    return None


def call_streamlit_api(base_url: str, url: str, use_interactive: bool = True, 
                      download_first: bool = False) -> Optional[Dict[str, Any]]:
    """
    Call Streamlit Cloud API and parse the response.
    This function provides the same interface as calling FastAPI directly.
    
    Args:
        base_url: Base URL of Streamlit Cloud app (e.g., "https://your-app.streamlit.app")
        url: Groww mutual fund URL to scrape
        use_interactive: Whether to use interactive browser
        download_first: Whether to download HTML first
        
    Returns:
        Parsed JSON response in the same format as FastAPI, or None if failed
        
    Example:
        >>> result = call_streamlit_api("https://app.streamlit.app", "https://groww.in/mutual-funds/...")
        >>> if result and result.get("success"):
        ...     print(result["data"])
    """
    try:
        response = requests.get(
            base_url,
            params={
                "api": "scrape",
                "url": url,
                "use_interactive": str(use_interactive).lower(),
                "download_first": str(download_first).lower()
            },
            timeout=300,  # 5 minutes timeout
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; API-Client/1.0)'
            }
        )
        response.raise_for_status()
        
        # Parse JSON from HTML
        parsed_data = parse_streamlit_json_response(response.text)
        
        if parsed_data is None:
            # If parsing failed, return error response
            return {
                "success": False,
                "error": "Failed to parse JSON from HTML response",
                "message": "Response parsing failed"
            }
        
        return parsed_data
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout",
            "message": "The request took too long to complete"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "message": "Failed to connect to API"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "An unexpected error occurred"
        }


# Example usage
if __name__ == "__main__":
    # Example: Call Streamlit Cloud API
    # Replace with your actual Streamlit Cloud URL
    base_url = "https://your-app.streamlit.app"
    fund_url = "https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth"
    
    print(f"Calling API: {base_url}")
    print(f"Scraping: {fund_url}")
    print("-" * 60)
    
    result = call_streamlit_api(base_url, fund_url)
    
    if result and result.get("success"):
        print("✅ Scraping successful!")
        print("\nScraped Data:")
        print(json.dumps(result["data"], indent=2))
    else:
        error_msg = result.get('error', 'Unknown error') if result else 'No response'
        print(f"❌ Scraping failed: {error_msg}")
        if result:
            print(f"Message: {result.get('message', 'N/A')}")

