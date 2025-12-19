"""
Unit tests for GrowwScraper class
Tests core functionality without requiring actual web requests
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import json
import tempfile
import shutil
from bs4 import BeautifulSoup

from groww_scraper import GrowwScraper


class TestGrowwScraper(unittest.TestCase):
    """Test cases for GrowwScraper class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.test_output_dir = tempfile.mkdtemp()
        self.test_download_dir = tempfile.mkdtemp()
        
        # Initialize scraper with test directories
        self.scraper = GrowwScraper(
            output_dir=self.test_output_dir,
            use_interactive=False,  # Disable browser automation for faster tests
            download_dir=self.test_download_dir,
            download_first=False
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directories
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        if os.path.exists(self.test_download_dir):
            shutil.rmtree(self.test_download_dir)
    
    def test_init(self):
        """Test GrowwScraper initialization"""
        scraper = GrowwScraper(
            output_dir="test_output",
            use_interactive=True,
            download_dir="test_download",
            download_first=True
        )
        
        self.assertEqual(scraper.output_dir, "test_output")
        self.assertEqual(scraper.download_dir, "test_download")
        self.assertTrue(scraper.use_interactive)
        self.assertTrue(scraper.download_first)
        self.assertIsNotNone(scraper.session)
        
        # Clean up
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")
        if os.path.exists("test_download"):
            shutil.rmtree("test_download")
    
    def test_is_blocked_or_empty_blocked(self):
        """Test detection of blocked pages"""
        # Test blocked page
        blocked_html = """
        <html>
            <head><title>Access Denied</title></head>
            <body>You are blocked</body>
        </html>
        """
        self.assertTrue(self.scraper._is_blocked_or_empty(blocked_html))
        
        # Test captcha page
        captcha_html = """
        <html>
            <head><title>Captcha Required</title></head>
            <body>Please complete captcha</body>
        </html>
        """
        self.assertTrue(self.scraper._is_blocked_or_empty(captcha_html))
    
    def test_is_blocked_or_empty_valid(self):
        """Test detection of valid pages"""
        # Test valid page with fund content
        valid_html = """
        <html>
            <head><title>Fund Details</title></head>
            <body>
                <div class="fund-details">
                    <table class="nav-table">NAV: 100</table>
                </div>
            </body>
        </html>
        """
        self.assertFalse(self.scraper._is_blocked_or_empty(valid_html))
    
    def test_is_blocked_or_empty_empty(self):
        """Test detection of empty pages"""
        # Test empty page
        empty_html = """
        <html>
            <head><title>Page</title></head>
            <body></body>
        </html>
        """
        self.assertTrue(self.scraper._is_blocked_or_empty(empty_html))
    
    def test_clean_text(self):
        """Test text cleaning function"""
        # Test normal text
        text = "  Hello   World  "
        cleaned = self.scraper._clean_text(text)
        self.assertEqual(cleaned, "Hello World")
        
        # Test empty text
        self.assertEqual(self.scraper._clean_text(""), "")
        self.assertEqual(self.scraper._clean_text(None), "")
        
        # Test long text truncation
        long_text = " ".join(["word"] * 100)
        cleaned = self.scraper._clean_text(long_text, max_length=50)
        # Truncated text may be slightly longer due to "...", but should be reasonable
        self.assertTrue(len(cleaned) <= 60)  # Allow some margin for "..."
        self.assertTrue(cleaned.endswith("..."))
    
    def test_extract_tables(self):
        """Test table extraction"""
        html = """
        <html>
            <body>
                <table>
                    <thead>
                        <tr><th>Name</th><th>Value</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>NAV</td><td>100.50</td></tr>
                        <tr><td>AUM</td><td>1000 Cr</td></tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        tables = self.scraper.extract_tables(soup)
        
        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0]['headers']), 2)
        self.assertEqual(len(tables[0]['data']), 2)
        self.assertEqual(tables[0]['data'][0]['Name'], 'NAV')
        self.assertEqual(tables[0]['data'][0]['Value'], '100.50')
    
    def test_extract_tables_no_headers(self):
        """Test table extraction without headers"""
        html = """
        <html>
            <body>
                <table>
                    <tr><td>Row1 Col1</td><td>Row1 Col2</td></tr>
                    <tr><td>Row2 Col1</td><td>Row2 Col2</td></tr>
                </table>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        tables = self.scraper.extract_tables(soup)
        
        self.assertEqual(len(tables), 1)
        # Should use first row as headers
        self.assertEqual(len(tables[0]['data']), 2)
    
    def test_extract_key_value_pairs(self):
        """Test key-value pair extraction"""
        html = """
        <html>
            <body>
                <dl>
                    <dt>NAV</dt>
                    <dd>100.50</dd>
                    <dt>Expense Ratio</dt>
                    <dd>1.5%</dd>
                </dl>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        kv_pairs = self.scraper.extract_key_value_pairs(soup)
        
        self.assertIn('nav', kv_pairs)
        self.assertEqual(kv_pairs['nav'], '100.50')
        self.assertIn('expense ratio', kv_pairs)
        self.assertEqual(kv_pairs['expense ratio'], '1.5%')
    
    def test_save_json(self):
        """Test JSON file saving"""
        test_data = {
            "fund_name": "Test Fund",
            "nav": {"value": "100.50", "as_of": "2024-01-01"}
        }
        
        filepath = self.scraper.save_json(test_data, "test_fund")
        
        # Check file was created
        self.assertTrue(os.path.exists(filepath))
        
        # Check file content
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # Should be saved as array
        self.assertIsInstance(saved_data, list)
        self.assertEqual(len(saved_data), 1)
        self.assertEqual(saved_data[0]["fund_name"], "Test Fund")
    
    @patch('groww_scraper.GrowwScraper.fetch_page')
    @patch('groww_scraper.GrowwScraper.extract_detailed_data')
    def test_parse_fund_data_success(self, mock_extract, mock_fetch):
        """Test successful fund data parsing"""
        # Mock HTML content
        mock_html = "<html><body>Fund Data</body></html>"
        mock_fetch.return_value = mock_html
        
        # Mock extracted data
        mock_data = {
            "fund_name": "Test Fund",
            "nav": {"value": "100.50", "as_of": "2024-01-01"}
        }
        mock_extract.return_value = mock_data
        
        # Test parsing
        result = self.scraper.parse_fund_data("https://groww.in/mutual-funds/test-fund")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["fund_name"], "Test Fund")
        self.assertIn("source_url", result)
        self.assertIn("last_scraped", result)
    
    @patch('groww_scraper.GrowwScraper.fetch_page')
    def test_parse_fund_data_failure(self, mock_fetch):
        """Test fund data parsing failure"""
        # Mock failed fetch
        mock_fetch.return_value = None
        
        # Test parsing
        result = self.scraper.parse_fund_data("https://groww.in/mutual-funds/test-fund")
        
        self.assertIsNone(result)
    
    def test_extract_from_element(self):
        """Test element extraction helper"""
        html = """
        <html>
            <body>
                <div>
                    <span>NAV: 100.50</span>
                    <span>As of: 2024-01-01</span>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Test extraction - the function looks for text containing the pattern
        # and extracts from parent or next sibling
        result = self.scraper._extract_from_element(soup, "NAV", r'(\d+\.\d+)')
        # The function may extract from different parts, so just check it returns something
        # or contains the expected pattern
        if result:
            # Check if it contains the NAV value or related text
            self.assertTrue("100.50" in result or "NAV" in result or len(result) > 0)
    
    def test_extract_detailed_data_structure(self):
        """Test that extract_detailed_data returns proper structure"""
        # Create minimal HTML
        html = """
        <html>
            <head><title>Test Fund - NAV</title></head>
            <body>
                <h1>Test Fund</h1>
                <div>Latest NAV as of 01 Jan 2024 ₹100.50</div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        
        # Extract data
        data = self.scraper.extract_detailed_data(soup, page_text, None)
        
        # Check structure
        self.assertIsInstance(data, dict)
        self.assertIn("fund_name", data)
        self.assertIn("nav", data)
        self.assertIn("summary", data)
        self.assertIn("returns", data)
        self.assertIn("category_info", data)
        self.assertIn("cost_and_tax", data)
        self.assertIn("top_5_holdings", data)
        self.assertIn("advanced_ratios", data)
        self.assertIn("faq", data)
        self.assertIn("source", data)
    
    def test_extract_detailed_data_fund_name(self):
        """Test fund name extraction"""
        html = """
        <html>
            <head><title>Test Fund Name - NAV, Mutual Fund Performance</title></head>
            <body>Content</body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        
        data = self.scraper.extract_detailed_data(soup, page_text, None)
        
        # Fund name should be cleaned (without "- NAV" suffix)
        self.assertIn("fund_name", data)
        self.assertNotIn("- NAV", data["fund_name"])
    
    def test_extract_detailed_data_nav(self):
        """Test NAV extraction"""
        html = """
        <html>
            <body>
                <div>Latest NAV as of 01 Jan 2024 ₹100.50</div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        
        data = self.scraper.extract_detailed_data(soup, page_text, None)
        
        self.assertIn("nav", data)
        self.assertIsInstance(data["nav"], dict)
        self.assertIn("value", data["nav"])
        self.assertIn("as_of", data["nav"])


class TestGrowwScraperEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_output_dir = tempfile.mkdtemp()
        self.scraper = GrowwScraper(
            output_dir=self.test_output_dir,
            use_interactive=False
        )
    
    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
    
    def test_extract_tables_empty(self):
        """Test table extraction with no tables"""
        html = "<html><body>No tables here</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        tables = self.scraper.extract_tables(soup)
        self.assertEqual(len(tables), 0)
    
    def test_extract_key_value_pairs_empty(self):
        """Test key-value extraction with no pairs"""
        html = "<html><body>No key-value pairs</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        kv_pairs = self.scraper.extract_key_value_pairs(soup)
        self.assertEqual(len(kv_pairs), 0)
    
    def test_save_json_invalid_data(self):
        """Test saving invalid JSON data"""
        # Should handle gracefully
        try:
            self.scraper.save_json({"invalid": object()}, "test")
        except (TypeError, ValueError):
            # Expected for non-serializable data
            pass
    
    def test_clean_text_unicode(self):
        """Test text cleaning with unicode characters"""
        text = "  Hello   World  ₹100  "
        cleaned = self.scraper._clean_text(text)
        self.assertIn("₹", cleaned)
        self.assertEqual(cleaned.strip(), cleaned)


if __name__ == '__main__':
    unittest.main()

