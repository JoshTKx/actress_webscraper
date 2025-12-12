# Backstage Actor Portfolio Scraper

A web scraper to collect actor portfolio images from Backstage.com. Built for educational purposes to learn web scraping, async Python, and system design principles.

## Project Structure

```
backstage-scraper/
├── src/                    # Source code
├── data/actors/           # Output directory for images
├── logs/                  # Log files
├── config/                # Configuration
├── venv/                  # Virtual environment (not in git)
├── requirements.txt       # Python dependencies
├── .env                   # Configuration file (not in git)
├── .env.example          # Configuration template
├── .gitignore            # Git ignore rules
└── verify_setup.py       # Setup verification script
```

## Setup Instructions

### 1. Virtual Environment

The virtual environment has been created. To activate it on Mac:

```bash
source venv/bin/activate
```

You'll know it's activated when you see `(venv)` at the start of your terminal prompt.

To deactivate later:

```bash
deactivate
```

### 2. Dependencies

All dependencies have been installed. They include:

- **httpx** - Modern async HTTP client for making web requests
- **beautifulsoup4 + lxml** - HTML parsing and extraction
- **aiofiles** - Async file I/O operations
- **tqdm** - Progress bars for long-running operations
- **python-dotenv** - Loads environment variables from .env file
- **loguru** - Beautiful, easy-to-use logging
- **Pillow** - Image processing and validation

### 3. Configuration (.env)

Your `.env` file contains the following settings:

#### Request Settings

- **REQUEST_DELAY=2.0** - Delay between requests (seconds). Set to 2.0 seconds to be polite and avoid overwhelming the server. This helps prevent getting blocked.
- **REQUEST_TIMEOUT=30.0** - Maximum time to wait for a response (seconds). Prevents hanging on slow connections.
- **MAX_CONCURRENT_REQUESTS=5** - Number of simultaneous requests. Lower is more polite; higher is faster but riskier.

#### User Agent

- **USER_AGENT** - Identifies your scraper to the server. Using a browser-like user agent helps avoid immediate bot detection.

#### Output Settings

- **OUTPUT_DIR=data/actors** - Where downloaded images will be saved
- **LOG_DIR=logs** - Where log files will be written

#### Scraping Behavior

- **RESPECT_ROBOTS_TXT=true** - Whether to check robots.txt before scraping (good practice!)
- **MAX_RETRIES=3** - How many times to retry failed requests

### 4. Verification

Run the verification script to test everything:

```bash
source venv/bin/activate
python verify_setup.py
```

## Why These Settings?

### Request Delay (2.0 seconds)

- **Why**: Prevents rate limiting and shows respect to the server
- **Too low**: Risk of getting IP banned
- **Too high**: Unnecessarily slow scraping

### Concurrent Requests (5)

- **Why**: Balance between speed and politeness
- **Too high**: Overwhelms server, gets blocked
- **Too low**: Wastes time waiting

### User Agent

- **Why**: Some sites block requests without a proper user agent
- **Best practice**: Use a real browser user agent string

### Respect Robots.txt

- **Why**: Legal and ethical - shows you're following web standards
- **Note**: Always check robots.txt before scraping any site

## Usage

### Complete Scraper (Recommended)

The main scraper combines listing scraping and profile image downloading:

```bash
# Scrape first 3 listing pages, process first 10 profiles
python src/main_scraper.py --max-listing-pages 3 --max-profiles 10

# Scrape all listing pages, process all profiles (careful - could be 100+ profiles!)
python src/main_scraper.py

# Resume from existing profile list (skips profiles that already have images)
python src/main_scraper.py --max-profiles 50

# Custom delay between profiles
python src/main_scraper.py --delay 3.0

# Scrape a single profile
python src/main_scraper.py --single --url "https://www.backstage.com/tal/username/" --name "actor-name"
```

### Individual Scrapers

**Listing Scraper** - Extract profile URLs from listing pages:

```bash
python src/listing_scraper.py
```

**Profile Scraper** - Download images from a single profile:

```bash
python src/profile_scraper.py
```

### Command Line Options

```
--max-listing-pages N    Limit number of listing pages to scrape
--max-profiles N         Limit number of profiles to process
--delay N                Delay between profiles (seconds, default: 2.0)
--no-resume              Don't resume from existing profile list
--no-skip-existing       Don't skip profiles that already have images
--profiles-file FILE     Custom profile list file (default: all_profiles.txt)
--single                 Scrape single profile mode
--url URL                Profile URL (for single mode)
--name NAME              Actor name (for single mode)
```

## Project Structure

```
backstage-scraper/
├── src/
│   ├── main_scraper.py      # Combined orchestrator (USE THIS!)
│   ├── listing_scraper.py   # Scrapes profile URLs from listing pages
│   └── profile_scraper.py   # Downloads images from individual profiles
├── data/actors/             # Output directory for images
├── logs/                    # Log files
├── all_profiles.txt         # Saved profile list (auto-generated)
└── requirements.txt         # Python dependencies
```

## Features

- ✅ **Multi-page listing scraping** - Automatically navigates through all listing pages
- ✅ **Profile image downloading** - Extracts and downloads all images from each profile
- ✅ **Resume support** - Can resume interrupted scrapes
- ✅ **Skip existing** - Automatically skips profiles that already have images
- ✅ **Rate limiting** - Polite delays between requests
- ✅ **Progress tracking** - Progress bars for long operations
- ✅ **Error handling** - Graceful error handling with detailed logging
- ✅ **Cloudflare bypass** - Uses CloudScraper to bypass bot protection

## Next Steps

1. ✅ Virtual environment created and activated
2. ✅ Dependencies installed
3. ✅ Configuration file created
4. ✅ Setup verified
5. ✅ Listing scraper built
6. ✅ Profile scraper built
7. ✅ Combined scraper built

**Ready to scrape!**

Start with a small test:

```bash
python src/main_scraper.py --max-listing-pages 1 --max-profiles 2
```

## Notes

- The HTTP connection test showed a 403 status, which is expected - Backstage.com has bot protection. Your scraper will need to handle this (proper headers, cookies, etc.).
- Always be respectful when scraping - use delays, respect robots.txt, and don't overload servers.
- This is for educational purposes - make sure you understand the legal and ethical implications of web scraping.
