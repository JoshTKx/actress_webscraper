#!/usr/bin/env python3
"""
Continue scraping from page 141 to 200.
This script will scrape the remaining pages and append to all_profiles.txt
"""

import sys
from pathlib import Path

sys.path.insert(0, 'src')

from listing_scraper import (
    scrape_listing_page,
    load_profile_list,
    save_profile_list,
    scraper
)
from loguru import logger
import time

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

def continue_scraping_from_page(start_page: int = 141, end_page: int = 200):
    """Continue scraping from a specific page number."""
    
    logger.info("="*70)
    logger.info(f"CONTINUING SCRAPING FROM PAGE {start_page} TO {end_page}")
    logger.info("="*70)
    
    # Load existing profiles
    existing_profiles = load_profile_list("all_profiles.txt")
    existing_urls = {url for url, _ in existing_profiles}
    logger.info(f"Loaded {len(existing_profiles)} existing profiles")
    
    # Scrape remaining pages
    new_profiles = []
    
    for page_num in range(start_page, end_page + 1):
        url = f"https://www.backstage.com/talent/?page={page_num}" if page_num > 1 else "https://www.backstage.com/talent/"
        
        logger.info(f"Scraping page {page_num}...")
        
        # Refresh session every 20 pages
        if page_num % 20 == 0:
            logger.info("Refreshing session...")
            scraper.get("https://www.backstage.com/", timeout=30)
            time.sleep(2)
        
        try:
            profiles = scrape_listing_page(url)
            
            if not profiles:
                logger.warning(f"No profiles found on page {page_num}, trying session refresh...")
                scraper.get("https://www.backstage.com/", timeout=30)
                time.sleep(2)
                profiles = scrape_listing_page(url)
                
                if not profiles:
                    logger.warning(f"Still no profiles on page {page_num}, stopping")
                    break
            
            # Filter out duplicates
            for profile_url, actor_name in profiles:
                if profile_url not in existing_urls:
                    new_profiles.append((profile_url, actor_name))
                    existing_urls.add(profile_url)
            
            logger.success(f"Page {page_num}: Found {len(profiles)} profiles ({len([p for p in profiles if p[0] not in existing_urls])} new)")
            
            # Save incrementally every 5 pages
            if page_num % 5 == 0:
                all_profiles = existing_profiles + new_profiles
                save_profile_list(all_profiles, "all_profiles.txt")
                logger.info(f"Saved {len(all_profiles)} total profiles (incremental save)")
            
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error on page {page_num}: {e}")
            logger.exception("Full traceback:")
            # Try to continue
            continue
    
    # Final save
    all_profiles = existing_profiles + new_profiles
    save_profile_list(all_profiles, "all_profiles.txt")
    
    logger.info("="*70)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*70)
    logger.success(f"Total profiles: {len(all_profiles)}")
    logger.success(f"New profiles added: {len(new_profiles)}")
    logger.info("="*70)
    
    return all_profiles

if __name__ == "__main__":
    # Establish session first
    logger.info("Establishing session...")
    scraper.get("https://www.backstage.com/", timeout=30)
    time.sleep(1)
    
    # Continue from page 141 to 200
    continue_scraping_from_page(141, 200)


