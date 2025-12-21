# Groww Mutual Fund Scraper

A comprehensive scraper for Groww mutual fund pages that extracts structured data and saves to JSON files.

## Features

- 📊 Scrapes comprehensive mutual fund data from Groww pages
- 🤖 Supports Playwright and Selenium for dynamic content
- 📁 Structured JSON output
- 🔄 Batch processing of multiple URLs
- 💾 Saves individual JSON files for each fund

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers (Optional but Recommended)

```bash
playwright install chromium
```

## Quick Start

### Method 1: Using Shell Script (Recommended)

**Linux/Mac:**
```bash
chmod +x scrape.sh
./scrape.sh
```

**Windows:**
```cmd
scrape.bat
```

### Method 2: Using Python Script Directly

```bash
python batch_scrape.py --file urls.txt
```

### Method 3: Command Line URLs

```bash
python batch_scrape.py https://groww.in/mutual-funds/fund1 https://groww.in/mutual-funds/fund2
```

## Usage

### 1. Prepare URLs File

Create a file named `urls.txt` (or use `-f` to specify a different file) with one URL per line:

```
https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth
https://groww.in/mutual-funds/sbi-large-midcap-fund-direct-growth
https://groww.in/mutual-funds/hdfc-top-100-fund-direct-growth
```

Lines starting with `#` are treated as comments and ignored.

### 2. Run the Scraper

**Using shell script:**
```bash
# Basic usage (uses urls.txt)
./scrape.sh

# Custom URLs file
./scrape.sh -f my_urls.txt

# Disable browser automation (faster, but may miss dynamic content)
./scrape.sh --no-interactive

# Download HTML first (more reliable, but slower)
./scrape.sh --download-first
```

**Using Python directly:**
```bash
# Basic usage
python batch_scrape.py --file urls.txt

# Custom output directory
python batch_scrape.py --file urls.txt --output-dir output/json_files

# Disable browser automation
python batch_scrape.py --file urls.txt --no-interactive

# Download HTML first
python batch_scrape.py --file urls.txt --download-first
```

### 3. Check Results

JSON files are saved in `data/mutual_funds/` directory (or your specified output directory).

A summary file `scraping_summary.json` is also created with:
- Total URLs processed
- Successful scrapes
- Failed scrapes
- List of generated files
- Error details

## Command Line Options

```
Options:
  -f, --file FILE          File containing URLs (one per line) [default: urls.txt]
  -o, --output-dir DIR     Output directory for JSON files [default: data/mutual_funds]
  --no-interactive         Disable browser automation (Playwright/Selenium)
  --download-first         Download HTML before scraping (slower but more reliable)
  -h, --help               Show help message
```

## Output Format

Each fund is saved as a separate JSON file with the following structure:

```json
[
  {
    "fund_name": "...",
    "nav": {
      "value": "₹100.50",
      "as_of": "01 Jan 2024"
    },
    "fund_size": "₹1,000Cr",
    "aum": "₹500Cr",
    "returns": {
      "1y": "12.5%",
      "3y": "15.2%",
      "5y": "18.0%",
      "since_inception": "16.5%"
    },
    "summary": {
      "fund_category": "Equity",
      "fund_type": "Large Cap",
      "risk_level": "Very High Risk",
      "lock_in_period": "",
      "rating": null
    },
    "minimum_investments": {
      "min_sip": "₹500",
      "min_first_investment": "₹5,000",
      "min_2nd_investment_onwards": "₹1,000"
    },
    "cost_and_tax": {
      "expense_ratio": "1.5%",
      "exit_load": "Nil",
      "stamp_duty": "0.005%",
      "tax_implication": "..."
    },
    "top_5_holdings": [...],
    "advanced_ratios": {...},
    "category_info": {...},
    "faq": [...],
    "source_url": "https://groww.in/mutual-funds/...",
    "last_scraped": "2024-01-15"
  }
]
```

## Examples

### Example 1: Basic Batch Scraping

```bash
# Create urls.txt with your URLs
echo "https://groww.in/mutual-funds/fund1" > urls.txt
echo "https://groww.in/mutual-funds/fund2" >> urls.txt

# Run scraper
./scrape.sh
```

### Example 2: Scrape Single URL

```bash
python batch_scrape.py https://groww.in/mutual-funds/nippon-india-large-cap-fund-direct-growth
```

### Example 3: Custom Output Directory

```bash
python batch_scrape.py --file urls.txt --output-dir output/funds
```

### Example 4: Fast Mode (No Browser)

```bash
python batch_scrape.py --file urls.txt --no-interactive
```

## Configuration

The scraper supports several configuration options:

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

### Scraping Fails

- Ensure Playwright/Selenium dependencies are installed
- Check that the target URL is accessible
- Try using `--download-first` for more reliable extraction
- Check error messages in `scraping_summary.json`

### Timeout Issues

- Some pages may take longer to load
- Consider using `--download-first` for better reliability
- Check your internet connection

## File Structure

```
.
├── groww_scraper.py          # Core scraper class
├── batch_scrape.py           # Batch scraping script
├── scrape.sh                 # Shell script (Linux/Mac)
├── scrape.bat                # Batch script (Windows)
├── urls.txt                  # URLs file template
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── data/
    ├── mutual_funds/         # Output JSON files
    └── downloaded_html/      # Temporary HTML files
```

## License

This project is provided as-is for educational and personal use.

## Support

For issues or questions, please check the code comments in `groww_scraper.py` for detailed implementation notes.
