#!/usr/bin/env python3
"""
Listing Scraper for Backstage.com
Scrapes profile URLs from listing pages with pagination support.
"""

import cloudscraper
from bs4 import BeautifulSoup
from pathlib import Path
import time
import re
import sys
from typing import List, Tuple, Optional
from urllib.parse import urljoin

from loguru import logger
from tqdm import tqdm

# Configure logger
logger.remove()  # Remove default handler

# Console handler (colored output)
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

# File handler (saves to logs/)
Path("logs").mkdir(exist_ok=True)
logger.add(
    "logs/listing_scraper_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)

# Create cloudscraper session (reusable for multiple requests)
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)


def investigate_listing_page():
    """Investigate the structure of the listing page and pagination."""
    url = "https://www.backstage.com/talent/"
    
    logger.info("="*70)
    logger.info("INVESTIGATING LISTING PAGE STRUCTURE")
    logger.info("="*70)
    
    # Visit homepage first to establish session
    logger.info("Establishing session by visiting homepage...")
    try:
        scraper.get("https://www.backstage.com/", timeout=30)
        time.sleep(1)  # Small delay
    except Exception as e:
        logger.warning(f"Homepage visit failed: {e}")
    
    logger.info(f"Fetching: {url}")
    try:
        response = scraper.get(url, timeout=30)
    except Exception as e:
        logger.error(f"Failed to fetch page: {e}")
        return
    
    logger.info(f"Status: {response.status_code}")
    logger.info(f"Content length: {len(response.text)} bytes")
    
    # Save HTML to file for inspection
    output_file = Path("listing_page_raw.html")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    logger.success(f"Saved HTML to: {output_file}")
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    # ========================================
    # PART 1: Find Profile Links
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("PART 1: PROFILE LINKS")
    logger.info("="*70)
    
    # Strategy 1: Look for links containing '/tal/'
    profile_links = soup.find_all('a', href=lambda x: x and '/tal/' in x)
    logger.info(f"Found {len(profile_links)} links containing '/tal/'")
    
    if profile_links:
        logger.info("\nFirst 5 profile links:")
        for i, link in enumerate(profile_links[:5], 1):
            href = link.get('href')
            text = link.get_text(strip=True)
            classes = link.get('class', [])
            logger.info(f"\n{i}. URL: {href}")
            logger.info(f"   Text: {text}")
            logger.info(f"   Classes: {classes}")
    
    # Strategy 2: Search raw HTML for profile URL pattern (relative and absolute)
    absolute_pattern = r'https://www\.backstage\.com/tal/[^/]+/'
    relative_pattern = r'/tal/([^/\"\s<>\)]+)'
    
    absolute_urls = re.findall(absolute_pattern, response.text)
    relative_paths = re.findall(relative_pattern, response.text)
    
    unique_absolute = list(set(absolute_urls))
    unique_relative = list(set(relative_paths))
    
    logger.info(f"\nFound {len(unique_absolute)} absolute profile URLs in raw HTML")
    logger.info(f"Found {len(unique_relative)} relative profile paths in raw HTML")
    
    if unique_relative:
        logger.info("\nFirst 5 relative paths:")
        for i, path in enumerate(unique_relative[:5], 1):
            logger.info(f"{i}. /tal/{path}")
    
    # ========================================
    # PART 2: Pagination Detection
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("PART 2: PAGINATION")
    logger.info("="*70)
    
    # Look for common pagination patterns
    pagination_found = False
    
    # Pattern 1: "Next" button/link
    next_buttons = soup.find_all('a', string=re.compile(r'next', re.I))
    if next_buttons:
        logger.info(f"Found {len(next_buttons)} 'Next' links:")
        for btn in next_buttons[:3]:
            href = btn.get('href')
            text = btn.get_text(strip=True)
            classes = btn.get('class', [])
            logger.info(f"   - href: {href}")
            logger.info(f"     text: {text}")
            logger.info(f"     classes: {classes}")
        pagination_found = True
    
    # Pattern 2: rel="next" attribute
    rel_next = soup.find_all('a', rel='next')
    if rel_next:
        logger.info(f"Found {len(rel_next)} links with rel='next':")
        for link in rel_next:
            logger.info(f"   - href: {link.get('href')}")
        pagination_found = True
    
    # Pattern 3: Page numbers (1, 2, 3, ...)
    page_numbers = soup.find_all('a', string=re.compile(r'^\d+$'))
    if page_numbers:
        logger.info(f"Found {len(page_numbers)} page number links:")
        for link in page_numbers[:5]:
            logger.info(f"   - Page {link.get_text()}: {link.get('href')}")
        pagination_found = True
    
    # Pattern 4: URL parameters (search for ?page= or &page=)
    if '?page=' in response.text or '&page=' in response.text:
        logger.info("Found URL parameter pagination (?page= or &page=)")
        page_urls = re.findall(r'href="([^"]*[?&]page=\d+[^"]*)"', response.text)
        if page_urls:
            logger.info(f"   Found {len(page_urls)} page URLs:")
            for url in page_urls[:5]:
                logger.info(f"   - {url}")
        pagination_found = True
    
    # Pattern 5: Pagination container/wrapper
    pagination_divs = soup.find_all(['div', 'nav', 'ul'], class_=re.compile(r'paginat', re.I))
    if pagination_divs:
        logger.info(f"Found {len(pagination_divs)} pagination containers:")
        for div in pagination_divs[:2]:
            logger.info(f"   - Tag: {div.name}")
            logger.info(f"   - Classes: {div.get('class')}")
            links = div.find_all('a')
            logger.info(f"   - Contains {len(links)} links")
    
    if not pagination_found:
        logger.warning("WARNING: No obvious pagination found!")
        logger.warning("   The page might use JavaScript-based pagination")
        logger.warning("   Or all profiles might be on one page")
    
    # ========================================
    # PART 3: Current Page Detection
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("PART 3: CURRENT PAGE INDICATOR")
    logger.info("="*70)
    
    # Look for indicators of current page (often has class 'active' or 'current')
    active_page = soup.find_all(['a', 'span'], class_=re.compile(r'active|current', re.I))
    if active_page:
        logger.info(f"Found {len(active_page)} active/current page indicators:")
        for elem in active_page[:3]:
            logger.info(f"   - Text: {elem.get_text(strip=True)}")
            logger.info(f"     Classes: {elem.get('class')}")
    
    # ========================================
    # SUMMARY
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("INVESTIGATION SUMMARY")
    logger.info("="*70)
    logger.info(f"Profile links found: {len(profile_links)} (via <a> tags)")
    logger.info(f"Profile URLs found: {len(unique_absolute)} absolute, {len(unique_relative)} relative (via regex in HTML)")
    logger.info(f"Pagination detected: {'YES' if pagination_found else 'NO'}")
    logger.info(f"\nRaw HTML saved to: {output_file}")
    logger.info("\nNext steps:")
    logger.info("1. Inspect listing_page_raw.html manually")
    logger.info("2. Look for pagination controls (Next button, page numbers)")
    logger.info("3. Check if pages use URL parameters (?page=2) or paths (/page/2/)")
    logger.info("4. Update the scraping logic based on findings")
    logger.info("="*70)


def _normalize_listing_url(href: str, base_url: str = None) -> str:
    """Convert relative URL to absolute URL for listing pages."""
    if not href:
        return None
    
    href = href.strip()
    
    # Already absolute
    if href.startswith('http://') or href.startswith('https://'):
        return href
    
    # Protocol-relative
    if href.startswith('//'):
        return f"https:{href}"
    
    # Absolute path
    if href.startswith('/'):
        return f"https://www.backstage.com{href}"
    
    # Relative path - combine with base_url
    if base_url:
        return urljoin(base_url, href)
    
    # Default to backstage.com
    return f"https://www.backstage.com/{href}"


def scrape_listing_page(page_url: str) -> List[Tuple[str, str]]:
    """
    Extract profile URLs and names from a single listing page.
    
    Args:
        page_url: URL of the listing page
        
    Returns:
        List of (profile_url, actor_name) tuples (should be ~50 per page)
    """
    try:
        logger.info(f"Fetching page: {page_url}")
        # Visit homepage first if this is the first page (establish session)
        if page_url == "https://www.backstage.com/talent/" or 'page=1' in page_url or 'page=' not in page_url:
            try:
                scraper.get("https://www.backstage.com/", timeout=30)
                time.sleep(1)
            except:
                pass
        
        response = scraper.get(page_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        profiles = []
        seen_urls = set()
        
        # Method 1: Find <a> tags with /tal/ in href
        profile_links = soup.find_all('a', href=lambda x: x and '/tal/' in x)
        
        for link in profile_links:
            href = link.get('href')
            
            # Build full URL
            if href.startswith('/'):
                profile_url = f"https://www.backstage.com{href}"
            elif not href.startswith('http'):
                continue
            else:
                profile_url = href
            
            # Ensure it ends with / and matches pattern
            if not re.match(r'https://www\.backstage\.com/tal/[^/]+/$', profile_url):
                continue
            
            # Skip duplicates
            if profile_url in seen_urls:
                continue
            seen_urls.add(profile_url)
            
            # Extract actor name
            actor_name = link.get_text(strip=True)
            if not actor_name:
                # Fallback: extract from URL (/tal/username/ -> username)
                match = re.search(r'/tal/([^/]+)/', profile_url)
                actor_name = match.group(1) if match else "unknown"
            
            # Clean actor name
            actor_name = actor_name.strip()
            if actor_name and len(actor_name) > 0:
                profiles.append((profile_url, actor_name))
        
        # Method 2: Regex search in raw HTML for relative URLs (primary method for JS-rendered pages)
        # Look for /tal/username patterns (relative URLs)
        profile_pattern = r'/tal/([^/\"\s<>\)]+)'
        matches = re.findall(profile_pattern, response.text)
        
        for username in matches:
            profile_url = f"https://www.backstage.com/tal/{username}/"
            if profile_url not in seen_urls:
                seen_urls.add(profile_url)
                # Try to extract name from context, or use username
                actor_name = username.replace('-', ' ').title()
                profiles.append((profile_url, actor_name))
        
        # Method 3: Regex search for absolute URLs (backup)
        if len(profiles) < 10:
            logger.warning("Few profiles found, trying absolute URL pattern")
            absolute_pattern = r'https://www\.backstage\.com/tal/([^/]+)/'
            matches = re.findall(absolute_pattern, response.text)
            
            for username in matches:
                profile_url = f"https://www.backstage.com/tal/{username}/"
                if profile_url not in seen_urls:
                    seen_urls.add(profile_url)
                    actor_name = username.replace('-', ' ').title()
                    profiles.append((profile_url, actor_name))
        
        logger.success(f"Extracted {len(profiles)} profiles from page")
        return profiles
        
    except Exception as e:
        logger.error(f"Failed to scrape page {page_url}: {e}")
        logger.exception("Full traceback:")
        return []


def find_next_page(soup: BeautifulSoup, current_url: str, html_text: str = None) -> Optional[str]:
    """
    Find the URL of the next page.
    
    Args:
        soup: BeautifulSoup object of current page
        current_url: Current page URL
        html_text: Raw HTML text (for regex searching if JS-rendered)
        
    Returns:
        Next page URL or None if no next page
    """
    # Strategy 1: Look for "Next" button/link
    next_link = soup.find('a', string=re.compile(r'next', re.I))
    if next_link:
        href = next_link.get('href')
        if href:
            normalized = _normalize_listing_url(href, current_url)
            if normalized:
                logger.debug(f"Found next page via 'Next' button: {normalized}")
                return normalized
    
    # Strategy 2: Look for rel="next"
    next_link = soup.find('a', rel='next')
    if next_link:
        href = next_link.get('href')
        if href:
            normalized = _normalize_listing_url(href, current_url)
            if normalized:
                logger.debug(f"Found next page via rel='next': {normalized}")
                return normalized
    
    # Strategy 3: Search raw HTML for page URLs (for JS-rendered pages)
    if html_text:
        # Look for ?page=2, ?page=3, etc. in the HTML
        page_url_pattern = r'https://www\.backstage\.com/talent/[^"\s<>\)]*[?&]page=(\d+)'
        page_matches = re.findall(page_url_pattern, html_text)
        if page_matches:
            page_numbers = [int(p) for p in page_matches]
            # Get current page number
            current_page = 1
            if '?page=' in current_url or '&page=' in current_url:
                match = re.search(r'[?&]page=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
            
            # Find next page number
            next_page = current_page + 1
            if next_page in page_numbers or next_page <= max(page_numbers):
                # Construct next URL
                if '?page=' in current_url or '&page=' in current_url:
                    next_url = re.sub(r'([?&]page=)\d+', f'\\g<1>{next_page}', current_url)
                else:
                    # Add page parameter
                    separator = '&' if '?' in current_url else '?'
                    next_url = f"{current_url}{separator}page={next_page}"
                logger.debug(f"Found next page via HTML search: {next_url}")
                return next_url
    
    # Strategy 4: URL parameter increment (?page=N)
    if '?page=' in current_url or '&page=' in current_url:
        match = re.search(r'[?&]page=(\d+)', current_url)
        if match:
            current_page = int(match.group(1))
            next_page = current_page + 1
            next_url = re.sub(r'([?&]page=)\d+', f'\\g<1>{next_page}', current_url)
            logger.debug(f"Incremented page parameter: {next_url}")
            return next_url
    else:
        # First page - try page 2
        separator = '&' if '?' in current_url else '?'
        next_url = f"{current_url}{separator}page=2"
        logger.debug(f"First page, trying page 2: {next_url}")
        # Verify page 2 exists by checking HTML
        if html_text and '?page=2' in html_text:
            return next_url
    
    # Strategy 5: Look for current page number and increment
    active_page = soup.find(['a', 'span'], class_=re.compile(r'active|current', re.I))
    if active_page:
        current_page_num = active_page.get_text(strip=True)
        if current_page_num.isdigit():
            next_page_num = int(current_page_num) + 1
            
            # Look for link with next page number
            next_page_link = soup.find('a', string=str(next_page_num))
            if next_page_link:
                href = next_page_link.get('href')
                if href:
                    normalized = _normalize_listing_url(href, current_url)
                    if normalized:
                        logger.debug(f"Found next page via page number {next_page_num}: {normalized}")
                        return normalized
    
    logger.debug("No next page found")
    return None


def scrape_all_listing_pages(
    base_url: str = "https://www.backstage.com/talent/",
    max_pages: Optional[int] = None,
    rate_limit: float = 2.0
) -> List[Tuple[str, str]]:
    """
    Scrape ALL listing pages by following pagination.
    
    Args:
        base_url: Starting URL for talent listing
        max_pages: Maximum pages to scrape (None = unlimited, all pages)
        rate_limit: Seconds to wait between pages (default: 2.0)
        
    Returns:
        List of all (profile_url, actor_name) tuples from all pages
        
    Example:
        # Scrape first 5 pages only (for testing)
        profiles = scrape_all_listing_pages(max_pages=5)
        
        # Scrape ALL pages (could be 100+!)
        profiles = scrape_all_listing_pages()
    """
    all_profiles = []
    current_url = base_url
    page_num = 1
    seen_urls = set()  # Track pages we've visited to avoid loops
    
    logger.info("="*70)
    logger.info("STARTING MULTI-PAGE SCRAPING")
    logger.info("="*70)
    logger.info(f"Base URL: {base_url}")
    logger.info(f"Max pages: {max_pages if max_pages else 'UNLIMITED (all pages)'}")
    logger.info(f"Rate limit: {rate_limit}s between pages")
    logger.info("="*70)
    
    # Establish session by visiting homepage first
    logger.info("Establishing session by visiting homepage...")
    try:
        scraper.get("https://www.backstage.com/", timeout=30)
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Homepage visit failed: {e}")
    
    while True:
        # Check if we've seen this URL before (prevent infinite loops)
        if current_url in seen_urls:
            logger.warning(f"Already visited {current_url}, stopping to prevent loop")
            break
        seen_urls.add(current_url)
        
        # Check max pages limit
        if max_pages and page_num > max_pages:
            logger.info(f"Reached max pages limit: {max_pages}")
            break
        
        logger.info(f"\nPage {page_num}: {current_url}")
        
        # Scrape current page
        try:
            profiles = scrape_listing_page(current_url)
            
            if not profiles:
                # If we got 403, try refreshing session and retry once
                if page_num > 1:  # Don't retry on first page
                    logger.warning(f"No profiles found on page {page_num}, might be session issue - refreshing session and retrying...")
                    try:
                        scraper.get("https://www.backstage.com/", timeout=30)
                        time.sleep(2)
                        profiles = scrape_listing_page(current_url)
                        if profiles:
                            logger.success(f"Retry successful! Found {len(profiles)} profiles on page {page_num}")
                        else:
                            logger.warning(f"Still no profiles after retry on page {page_num}, might be end of pagination")
                            break
                    except Exception as retry_e:
                        logger.error(f"Retry failed: {retry_e}")
                        break
                else:
                    logger.warning(f"No profiles found on page {page_num}, might be end of pagination")
                    break
            
            # Add to collection
            before_count = len(all_profiles)
            all_profiles.extend(profiles)
            after_count = len(all_profiles)
            new_count = after_count - before_count
            
            logger.success(f"Page {page_num}: +{new_count} profiles (Total: {len(all_profiles)})")
            
            # Save incrementally every 10 pages (so file is updated during long scrapes)
            if page_num % 10 == 0:
                save_profile_list(all_profiles, "all_profiles.txt")
                logger.info(f"Saved {len(all_profiles)} profiles to file (incremental save every 10 pages)")
            
            # Find next page
            response = scraper.get(current_url, timeout=30)
            soup = BeautifulSoup(response.text, 'lxml')
            next_url = find_next_page(soup, current_url, response.text)
            
            if not next_url:
                logger.info("No more pages found - reached the end!")
                break
            
            current_url = next_url
            page_num += 1
            
            # Rate limiting (be polite!)
            logger.debug(f"Waiting {rate_limit}s before next page...")
            time.sleep(rate_limit)
            
        except Exception as e:
            logger.error(f"Error on page {page_num}: {e}")
            logger.exception("Full traceback:")
            logger.info("Stopping pagination due to error")
            break
    
    # Final summary
    logger.info("\n" + "="*70)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*70)
    logger.success(f"Pages scraped: {page_num}")
    logger.success(f"Total profiles found: {len(all_profiles)}")
    if page_num > 0:
        logger.info(f"Expected: ~{page_num * 50} profiles (50 per page)")
    
    # Final save (ensure all profiles are saved)
    save_profile_list(all_profiles, "all_profiles.txt")
    logger.info("Final profile list saved to all_profiles.txt")
    logger.info("="*70)
    
    return all_profiles


def save_profile_list(profiles: List[Tuple[str, str]], output_file: str = "profiles.txt") -> Path:
    """Save profile list to file."""
    output_path = Path(output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Backstage Profile URLs - {len(profiles)} profiles\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Format: URL | Actor Name\n\n")
        
        for url, name in profiles:
            f.write(f"{url} | {name}\n")
    
    logger.success(f"Saved {len(profiles)} profiles to: {output_path}")
    return output_path


def load_profile_list(input_file: str = "profiles.txt") -> List[Tuple[str, str]]:
    """Load profile list from file."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        return []
    
    profiles = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ' | ' in line:
                url, name = line.split(' | ', 1)
                profiles.append((url.strip(), name.strip()))
    
    logger.info(f"Loaded {len(profiles)} profiles from: {input_path}")
    return profiles


if __name__ == "__main__":
    # ========================================
    # STEP 1: INVESTIGATION (Run this first!)
    # ========================================
    # logger.info("\n" + "="*70)
    # logger.info("STEP 1: INVESTIGATING PAGE STRUCTURE")
    # logger.info("="*70)
    # investigate_listing_page()
    # 
    # logger.info("\n" + "="*70)
    # logger.info("Inspect 'listing_page_raw.html' before continuing")
    # logger.info("Once ready, uncomment STEP 2 or STEP 3 below")
    # logger.info("="*70)
    
    # ========================================
    # STEP 2: TEST SINGLE PAGE (Uncomment after investigation)
    # ========================================
    # logger.info("\n" + "="*70)
    # logger.info("STEP 2: TESTING SINGLE PAGE")
    # logger.info("="*70)
    # profiles = scrape_listing_page("https://www.backstage.com/talent/")
    # logger.info(f"Found {len(profiles)} profiles on first page")
    # 
    # if profiles:
    #     logger.info("\nFirst 5 profiles:")
    #     for i, (url, name) in enumerate(profiles[:5], 1):
    #         logger.info(f"{i}. {name} -> {url}")
    #     save_profile_list(profiles, "profiles_page1.txt")
    
    # ========================================
    # STEP 3: SCRAPE MULTIPLE PAGES (Uncomment when ready)
    # ========================================
    # logger.info("\n" + "="*70)
    # logger.info("STEP 3: SCRAPING MULTIPLE PAGES")
    # logger.info("="*70)
    # 
    # # Option A: Test with first 3 pages only
    # all_profiles = scrape_all_listing_pages(max_pages=3)
    # 
    # # Option B: Scrape ALL pages (could be 50-100+ pages!)
    # # all_profiles = scrape_all_listing_pages()  # CAREFUL!
    # 
    # if all_profiles:
    #     save_profile_list(all_profiles, "all_profiles.txt")
    #     logger.info(f"\nComplete! Scraped {len(all_profiles)} total profiles")
    
    # This module is typically imported by main_scraper.py
    # For standalone testing, uncomment one of the steps above
    pass

