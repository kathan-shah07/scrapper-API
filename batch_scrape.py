"""
Batch Scraper for Groww Mutual Funds
Scrapes multiple URLs and generates JSON files
"""

import sys
import os
import json
from typing import List, Dict, Any
from urllib.parse import urlparse

from groww_scraper import GrowwScraper


def get_fund_slug_from_url(url: str) -> str:
    """
    Extract fund slug from URL for filename.
    
    Args:
        url: Groww mutual fund URL
        
    Returns:
        Fund slug for filename
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    # Get last part of path (fund name)
    fund_slug = path_parts[-1] if path_parts else "unknown"
    return fund_slug


def scrape_urls(urls: List[str], output_dir: str = "data/mutual_funds", 
                use_interactive: bool = True, download_first: bool = False) -> Dict[str, Any]:
    """
    Scrape multiple URLs and save JSON files.
    
    Args:
        urls: List of URLs to scrape
        output_dir: Directory to save JSON files
        use_interactive: Use Playwright/Selenium for dynamic content
        download_first: Download HTML before scraping
        
    Returns:
        Dictionary with scraping results
    """
    scraper = GrowwScraper(
        output_dir=output_dir,
        use_interactive=use_interactive,
        download_dir="data/downloaded_html",
        download_first=download_first
    )
    
    results = {
        "total": len(urls),
        "successful": 0,
        "failed": 0,
        "files": [],
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"Starting batch scraping of {len(urls)} URL(s)")
    print(f"{'='*60}\n")
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        print("-" * 60)
        
        try:
            # Scrape the URL
            data = scraper.parse_fund_data(url)
            
            if data:
                # Extract fund slug from URL
                fund_slug = get_fund_slug_from_url(url)
                
                # Save JSON file
                filepath = scraper.save_json(data, fund_slug)
                
                results["successful"] += 1
                results["files"].append({
                    "url": url,
                    "filepath": filepath,
                    "status": "success"
                })
                
                print(f"✅ Successfully scraped and saved: {filepath}")
            else:
                results["failed"] += 1
                results["errors"].append({
                    "url": url,
                    "error": "Failed to scrape - no data returned"
                })
                print(f"❌ Failed to scrape: {url}")
        
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "url": url,
                "error": str(e)
            })
            print(f"❌ Error scraping {url}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    print(f"\n{'='*60}")
    print("Scraping Summary")
    print(f"{'='*60}")
    print(f"Total URLs: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"{'='*60}\n")
    
    # Save summary to file
    summary_file = os.path.join(output_dir, "scraping_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Summary saved to: {summary_file}")
    
    return results


def load_urls_from_file(filepath: str) -> List[str]:
    """
    Load URLs from a text file (one URL per line).
    
    Args:
        filepath: Path to file containing URLs
        
    Returns:
        List of URLs
    """
    urls = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    urls.append(line)
        return urls
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return []


def main():
    """Main function for batch scraping."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch scrape Groww mutual fund pages')
    parser.add_argument('urls', nargs='*', help='URLs to scrape (or use --file)')
    parser.add_argument('--file', '-f', help='File containing URLs (one per line)')
    parser.add_argument('--output-dir', '-o', default='data/mutual_funds', 
                       help='Output directory for JSON files (default: data/mutual_funds)')
    parser.add_argument('--no-interactive', action='store_true',
                       help='Disable interactive browser (Playwright/Selenium)')
    parser.add_argument('--download-first', action='store_true',
                       help='Download HTML before scraping')
    
    args = parser.parse_args()
    
    # Get URLs
    urls = []
    if args.file:
        urls = load_urls_from_file(args.file)
        if not urls:
            print(f"No URLs found in file: {args.file}")
            return
    elif args.urls:
        urls = args.urls
    else:
        # Try to load from default file
        default_file = "urls.txt"
        if os.path.exists(default_file):
            urls = load_urls_from_file(default_file)
            if urls:
                print(f"Loaded {len(urls)} URL(s) from {default_file}")
            else:
                print(f"No URLs found in {default_file}")
        else:
            print("Error: No URLs provided. Use --file or provide URLs as arguments.")
            print("Example: python batch_scrape.py https://groww.in/mutual-funds/...")
            print("Or create a urls.txt file with one URL per line")
            return
    
    if not urls:
        print("No URLs to scrape")
        return
    
    # Scrape URLs
    results = scrape_urls(
        urls=urls,
        output_dir=args.output_dir,
        use_interactive=not args.no_interactive,
        download_first=args.download_first
    )
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()

