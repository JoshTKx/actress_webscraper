#!/usr/bin/env python3
"""
Profile Scraper for Backstage.com
Scrapes images from a single actor profile page.
"""

import cloudscraper
from pathlib import Path
import time
from typing import List
import re
from urllib.parse import urljoin
from dataclasses import dataclass
import sys

from loguru import logger
from tqdm import tqdm
from PIL import Image


# Configuration Class
@dataclass
class ScraperConfig:
    """Configuration for the scraper."""
    
    # Directories
    output_dir: Path = Path("data/actors")
    log_dir: Path = Path("logs")
    
    # Rate limiting
    rate_limit_delay: float = 1.0  # seconds between requests
    
    # Retry settings
    max_retries: int = 3
    request_timeout: int = 30
    
    # Image validation
    min_image_width: int = 100
    min_image_height: int = 100
    min_file_size: int = 1024  # bytes


# Create global config instance
config = ScraperConfig()

# Create necessary directories
config.output_dir.mkdir(parents=True, exist_ok=True)
config.log_dir.mkdir(parents=True, exist_ok=True)

# Configure logger
logger.remove()  # Remove default handler

# Console handler (colored output)
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

# File handler (saves to logs/)
logger.add(
    str(config.log_dir / "scraper_{time:YYYY-MM-DD}.log"),
    rotation="1 day",      # Create new file each day
    retention="7 days",    # Keep logs for 7 days
    level="DEBUG"          # Save everything to file
)

# Create cloudscraper session (reusable for multiple requests)
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)


def fetch_with_retry(url: str, max_retries: int = None, timeout: int = None, stream: bool = False):
    """
    Fetch URL with automatic retry on failure.
    
    Uses exponential backoff: 1s, 2s, 4s between retries.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts (default: from config)
        timeout: Request timeout in seconds (default: from config)
        stream: Whether to stream the response (default: False)
        
    Returns:
        Response object if successful
        
    Raises:
        Exception if all retries fail
    """
    if max_retries is None:
        max_retries = config.max_retries
    if timeout is None:
        timeout = config.request_timeout
    
    for attempt in range(max_retries):
        try:
            response = scraper.get(url, timeout=timeout, stream=stream)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed, give up
                raise
            
            # Calculate wait time with exponential backoff
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            logger.debug(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    # Should never reach here, but just in case
    raise Exception("All retry attempts failed")


def validate_image(file_path: Path) -> bool:
    """
    Validate that the downloaded file is a real, non-corrupt image.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        True if valid image, False otherwise
    """
    try:
        # Open and verify the image
        with Image.open(file_path) as img:
            img.verify()  # Check if it's a valid image
        
        # Check minimum dimensions
        with Image.open(file_path) as img:
            width, height = img.size
            if width < config.min_image_width or height < config.min_image_height:
                logger.warning(f"Image too small: {width}x{height}px (min: {config.min_image_width}x{config.min_image_height})")
                return False
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size < config.min_file_size:
            logger.warning(f"Image file too small: {file_size} bytes (min: {config.min_file_size})")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Invalid image {file_path.name}: {e}")
        return False


def is_image_url(url: str) -> bool:
    """
    Check if URL points to an image (not video/audio).
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be an image, False otherwise
    """
    if not url:
        return False
    
    url_lower = url.lower()
    non_image_patterns = [
        'youtube', '.mp3', '.mp4', '.wav', '.m4a', '.avi', '.mov',
        'linkedin.com/collect', 'facebook.com/tr', 'google-analytics',
        'doubleclick', 'googlesyndication', 'adservice', 'ads.', 'pixel'
    ]
    
    # Check if URL contains any non-image patterns
    if any(pattern in url_lower for pattern in non_image_patterns):
        return False
    
    # Check if URL has image-like extension (optional, but helpful)
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    has_image_extension = any(url_lower.endswith(ext) for ext in image_extensions)
    
    # If it has an image extension, it's definitely an image
    # If it doesn't have a non-image pattern, assume it might be an image
    return has_image_extension or not any(pattern in url_lower for pattern in non_image_patterns)


def scrape_profile(profile_url: str) -> List[str]:
    """
    Extract all image URLs from a profile page.
    
    Uses regex-based extraction since the page is JavaScript-rendered:
    - Strategy 5: Search HTML text for cloudfront.net image URLs (primary method)
    - Strategy 6: Generic image URL search (fallback)
    
    Args:
        profile_url: URL of the profile page to scrape
        
    Returns:
        List of image URLs (full-size images only)
    """
    logger.info(f"Fetching profile: {profile_url}")
    
    try:
        # Fetch the page with retry logic
        response = fetch_with_retry(profile_url)
        
        image_urls = []
        
        # Strategy 5: Search HTML text for cloudfront.net image URLs (primary method)
        # This works for JavaScript-rendered pages where data-gallery attributes aren't in initial HTML
        logger.debug("Searching HTML text for cloudfront.net image URLs")
        # Look for cloudfront.net URLs that are images
        # Pattern matches URLs that may have malformed prefixes
        cloudfront_pattern = r'(?:https?://(?:www\.backstage\.com)?)?https://[^"\s<>\)]+cloudfront\.net[^"\s<>\)]+\.(jpg|jpeg|png|gif|webp)'
        # Reconstruct full URLs
        for match in re.finditer(cloudfront_pattern, response.text, re.IGNORECASE):
            url = match.group(0)
            # Clean up malformed URLs
            url = _normalize_url(url)
            if not url:
                continue
            
            # Filter out placeholders, favicons, and thumbnails
            url_lower = url.lower()
            if (is_image_url(url) and 
                'placeholder' not in url_lower and 
                'favicon' not in url_lower and
                'icon' not in url_lower and
                'casting_call' in url_lower):  # Focus on casting_call directory
                # Prefer full-size images over thumbnails
                # Thumbnails have 'c3F1YXJlX3RodW1i' (base64 for "square_thumb") in the filename
                # Full-size images have 'bWFpbi' (base64 for "main") or don't have thumb indicators
                if ('c3f1yxjlx3rodw1i' not in url_lower and 
                    'square_thumb' not in url_lower and 
                    'thumb' not in url_lower):
                    image_urls.append(url)
        
        # Strategy 6: Search HTML text for any image URLs (fallback if Strategy 5 finds nothing)
        if not image_urls:
            logger.debug("Fallback: Searching HTML text for any image URLs")
            # Look for URLs that look like images
            url_pattern = r'https?://[^\s"\'<>\)]+\.(jpg|jpeg|png|gif|webp)(?:\?[^\s"\'<>\)]*)?'
            for match in re.finditer(url_pattern, response.text, re.IGNORECASE):
                url = match.group(0)
                url = _normalize_url(url)
                if url and is_image_url(url) and 'placeholder' not in url.lower():
                    image_urls.append(url)
        
        # Remove duplicates using multiple strategies
        # Group URLs by image ID, then select the best URL for each image
        image_id_to_urls = {}
        
        for url in image_urls:
            # Normalize URL by removing query parameters and fragments for comparison
            normalized = _normalize_url_for_comparison(url)
            if not normalized:
                continue
            
            # Extract image ID (UUID) from URL to identify same image with different suffixes
            image_id = _extract_image_id_from_url(url)
            
            if image_id:
                # Group URLs by image ID
                if image_id not in image_id_to_urls:
                    image_id_to_urls[image_id] = []
                image_id_to_urls[image_id].append(url)
            else:
                # No image ID found, treat as unique
                image_id_to_urls[normalized] = [url]
        
        # Select best URL for each image ID
        # Prefer URLs with base64 suffix (full-size) over plain UUID URLs
        unique_urls = []
        seen_urls = set()
        
        for image_id, urls in image_id_to_urls.items():
            # Remove exact duplicates first
            unique_group_urls = list(dict.fromkeys(urls))  # Preserves order
            
            # Prefer URL with base64 suffix (indicates full-size/main image)
            # Look for URLs with '-bWFpbi' (base64 for "main") or other size indicators
            preferred_url = None
            for url in unique_group_urls:
                url_lower = url.lower()
                # Prefer URLs with base64 suffix over plain UUID
                if '-bwfpbi' in url_lower or len(url) > len(unique_group_urls[0]) + 20:
                    preferred_url = url
                    break
            
            # If no preferred URL found, use the first one
            if not preferred_url:
                preferred_url = unique_group_urls[0]
            
            # Add to unique list if not already seen
            normalized = _normalize_url_for_comparison(preferred_url)
            if normalized and normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_urls.append(preferred_url)
        
        logger.success(f"Found {len(unique_urls)} unique image URLs (from {len(image_urls)} total)")
        return unique_urls
        
    except Exception as e:
        logger.error(f"Error scraping profile: {e}")
        logger.exception("Full traceback:")
        return []


def _extract_image_id_from_url(url: str) -> str:
    """
    Extract the image ID (UUID) from a Backstage.com image URL.
    
    Backstage URLs have format: .../uuid-base64suffix.jpg
    This extracts the UUID part to identify the same image.
    
    Args:
        url: Image URL
        
    Returns:
        Image ID (UUID) if found, None otherwise
    """
    if not url:
        return None
    
    # Pattern: UUID format (8-4-4-4-12 hex digits)
    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', url, re.IGNORECASE)
    if match:
        return match.group(1).lower()  # Normalize to lowercase
    return None


def _normalize_url_for_comparison(url: str) -> str:
    """
    Normalize URL for comparison by removing query parameters and fragments.
    This helps identify duplicate images even if URLs have different parameters.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL without query parameters and fragments
    """
    if not url:
        return None
    
    from urllib.parse import urlparse, urlunparse
    
    try:
        parsed = urlparse(url)
        # Remove query and fragment, keep the rest
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            '',  # Remove query
            ''   # Remove fragment
        ))
        return normalized
    except:
        return url


def _normalize_url(url: str, base_url: str = None) -> str:
    """
    Normalize a URL (handle relative URLs, etc.).
    
    Args:
        url: URL to normalize (can be absolute or relative)
        base_url: Base URL to use for relative URLs
        
    Returns:
        Normalized absolute URL, or None if invalid
    """
    if not url:
        return None
    
    # Strip whitespace
    url = url.strip()
    
    # Fix malformed URLs that have double prefixes (e.g., "https://www.backstage.comhttps://...")
    if 'https://www.backstage.comhttps://' in url:
        url = url.replace('https://www.backstage.comhttps://', 'https://')
    if 'http://www.backstage.comhttp://' in url:
        url = url.replace('http://www.backstage.comhttp://', 'http://')
    if 'https://www.backstage.comhttp://' in url:
        url = url.replace('https://www.backstage.comhttp://', 'https://')
    
    # Already a full URL - return as-is
    if url.startswith('http://') or url.startswith('https://'):
        return url
    
    # Handle protocol-relative URLs (//example.com)
    if url.startswith('//'):
        return f"https:{url}"
    
    # Handle absolute paths (starting with /)
    if url.startswith('/'):
        return f"https://www.backstage.com{url}"
    
    # If base_url provided and URL is relative, combine them
    if base_url:
        return urljoin(base_url, url)
    
    # If no base_url and URL doesn't start with http, it's invalid
    return None


def download_image(image_url: str, save_path: Path) -> bool:
    """
    Download and validate an image.
    
    Args:
        image_url: URL of the image to download
        save_path: Full path where to save the image (including filename)
        
    Returns:
        True if download succeeded, False otherwise
    """
    try:
        # Download with retry logic
        response = fetch_with_retry(image_url, stream=True)
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'image' not in content_type:
            logger.warning(f"Not an image (Content-Type: {content_type}): {image_url[:80]}...")
            # Continue anyway - sometimes servers don't set content-type correctly
        
        # Ensure directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify file was written correctly
        if not save_path.exists():
            logger.error(f"File was not created: {save_path}")
            return False
        
        file_size = save_path.stat().st_size
        if file_size == 0:
            logger.error(f"File is empty: {save_path}")
            save_path.unlink()  # Delete empty file
            return False
        
        # Validate the downloaded image
        if not validate_image(save_path):
            logger.error(f"Downloaded file is corrupt, deleting: {save_path.name}")
            save_path.unlink()  # Delete corrupt file
            return False
        
        logger.success(f"Downloaded and validated: {save_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {image_url[:80]}...: {e}")
        # Try to clean up if file was partially written
        if save_path.exists():
            try:
                save_path.unlink()
            except:
                pass
        return False


def scrape_and_download_profile(profile_url: str, actor_name: str) -> None:
    """
    Main function: scrape profile and download all images with progress tracking.
    
    Args:
        profile_url: URL of the profile page to scrape
        actor_name: Name to use for the output folder (e.g., "jonathan-cantor")
    """
    # Track statistics
    stats = {
        'total_found': 0,
        'successful': 0,
        'failed': 0,
        'failed_urls': [],
        'start_time': time.time()
    }
    
    logger.info("="*60)
    logger.info(f"Starting scrape for: {actor_name}")
    logger.info(f"Profile URL: {profile_url}")
    logger.info("="*60)
    
    # Step 1: Scrape profile
    try:
        image_urls = scrape_profile(profile_url)
        stats['total_found'] = len(image_urls)
        logger.info(f"Found {len(image_urls)} images")
    except Exception as e:
        logger.error(f"Failed to scrape profile: {e}")
        logger.exception("Full traceback:")
        return
    
    if not image_urls:
        logger.warning("No images found, exiting")
        return
    
    # Step 2: Create output directory
    output_dir = config.output_dir / actor_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Step 3: Download with progress bar
    logger.info(f"Starting download of {len(image_urls)} images...")
    
    with tqdm(
        total=len(image_urls),
        desc=f"Downloading {actor_name}",
        unit="img",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    ) as pbar:
        
        for idx, image_url in enumerate(image_urls, start=1):
            # Generate filename: image_001.jpg, image_002.jpg, etc.
            # Try to preserve original extension if possible
            extension = '.jpg'  # Default
            url_lower = image_url.lower()
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                if ext in url_lower:
                    extension = ext
                    break
            
            filename = f"image_{idx:03d}{extension}"
            save_path = output_dir / filename
            
            # Download image
            if download_image(image_url, save_path):
                stats['successful'] += 1
            else:
                stats['failed'] += 1
                stats['failed_urls'].append(image_url)
            
            # Update progress bar
            pbar.update(1)
            
            # Rate limiting (be polite)
            if idx < len(image_urls):  # Don't delay after last image
                time.sleep(config.rate_limit_delay)
    
    # Calculate duration
    stats['duration'] = time.time() - stats['start_time']
    
    # Step 4: Print detailed summary
    logger.info("="*60)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*60)
    logger.info(f"Profile: {actor_name}")
    logger.info(f"Total images found: {stats['total_found']}")
    logger.success(f"Successfully downloaded: {stats['successful']}")
    
    if stats['failed'] > 0:
        logger.error(f"Failed downloads: {stats['failed']}")
        logger.info("Failed URLs:")
        for url in stats['failed_urls']:
            logger.info(f"  - {url[:100]}...")
    
    if stats['total_found'] > 0:
        logger.info(f"Total time: {stats['duration']:.1f}s")
        logger.info(f"Average time per image: {stats['duration']/stats['total_found']:.1f}s")
    
    logger.info(f"Output directory: {output_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    # Test with one profile
    test_url = "https://www.backstage.com/tal/jonathancantor/"
    test_name = "jonathan-cantor"
    
    scrape_and_download_profile(test_url, test_name)
