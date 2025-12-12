#!/usr/bin/env python3
"""
Main Scraper Orchestrator for Backstage.com
Combines listing scraper and profile scraper to:
1. Scrape all profile URLs from listing pages
2. Download images from each profile
"""

import sys
from pathlib import Path
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from loguru import logger
from tqdm import tqdm

# Import our scrapers
from listing_scraper import (
    scrape_all_listing_pages,
    save_profile_list,
    load_profile_list,
    scrape_listing_page
)
from profile_scraper import (
    scrape_and_download_profile,
    scrape_profile,
    download_image,
    config as profile_config
)


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
    "logs/main_scraper_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


@dataclass
class MainScraperConfig:
    """Configuration for the main scraper orchestrator."""
    
    # Profile list file
    profiles_file: str = "all_profiles.txt"
    
    # Scraping limits (for testing)
    max_listing_pages: Optional[int] = None  # None = all pages
    max_profiles: Optional[int] = None  # None = all profiles
    
    # Rate limiting
    delay_between_profiles: float = 2.0  # seconds between profiles
    
    # Parallelization
    max_workers_profiles: int = 3  # Number of profiles to process concurrently
    max_workers_images: int = 5  # Number of images to download concurrently per profile
    
    # Resume support
    resume_from_file: bool = True  # Load existing profile list if available
    skip_existing: bool = True  # Skip profiles that already have images downloaded


def process_single_profile_parallel(
    profile_url: str,
    actor_name: str,
    skip_existing: bool,
    max_workers_images: int,
    stats_lock: threading.Lock,
    stats: dict
) -> Tuple[bool, str]:
    """
    Process a single profile (scrape + download images) with parallel image downloads.
    
    Returns:
        (success: bool, message: str)
    """
    try:
        # Check if already processed
        if skip_existing:
            output_dir = profile_config.output_dir / actor_name
            if output_dir.exists():
                has_images = (
                    any(output_dir.glob("image_*.jpg")) or
                    any(output_dir.glob("image_*.png")) or
                    any(output_dir.glob("image_*.jpeg")) or
                    any(output_dir.glob("image_*.gif")) or
                    any(output_dir.glob("image_*.webp"))
                )
                if has_images:
                    with stats_lock:
                        stats['skipped'] += 1
                    return True, f"Skipped {actor_name} (already has images)"
        
        # Scrape profile to get image URLs
        image_urls = scrape_profile(profile_url)
        
        if not image_urls:
            with stats_lock:
                stats['processed'] += 1
            return False, f"No images found for {actor_name}"
        
        # Create output directory
        output_dir = profile_config.output_dir / actor_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download images in parallel
        successful = 0
        failed = 0
        
        def download_single_image(args):
            idx, image_url = args
            extension = '.jpg'
            url_lower = image_url.lower()
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                if ext in url_lower:
                    extension = ext
                    break
            
            filename = f"image_{idx:03d}{extension}"
            save_path = output_dir / filename
            
            if download_image(image_url, save_path):
                return True
            return False
        
        # Download images in parallel
        with ThreadPoolExecutor(max_workers=max_workers_images) as executor:
            image_args = [(idx, url) for idx, url in enumerate(image_urls, start=1)]
            results = list(executor.map(download_single_image, image_args))
            
            successful = sum(results)
            failed = len(results) - successful
        
        with stats_lock:
            stats['processed'] += 1
            if successful > 0:
                stats['successful'] += 1
            if failed > 0:
                stats['failed'] += 1
                stats['failed_profiles'].append((profile_url, actor_name))
        
        return True, f"{actor_name}: {successful}/{len(image_urls)} images downloaded"
        
    except Exception as e:
        with stats_lock:
            stats['processed'] += 1
            stats['failed'] += 1
            stats['failed_profiles'].append((profile_url, actor_name))
        return False, f"Error processing {actor_name}: {e}"


def scrape_all_profiles(
    max_listing_pages: Optional[int] = None,
    max_profiles: Optional[int] = None,
    delay_between_profiles: float = 2.0,
    resume_from_file: bool = True,
    skip_existing: bool = True,
    profiles_file: str = "all_profiles.txt",
    max_workers_profiles: int = 3,
    max_workers_images: int = 5
) -> None:
    """
    Complete workflow: Scrape listing pages → Download images from each profile.
    
    Args:
        max_listing_pages: Maximum listing pages to scrape (None = all)
        max_profiles: Maximum profiles to process (None = all)
        delay_between_profiles: Seconds to wait between profiles (not used in parallel mode)
        resume_from_file: Load existing profile list if available
        skip_existing: Skip profiles that already have downloaded images
        profiles_file: File to save/load profile list
        max_workers_profiles: Number of profiles to process concurrently (default: 3)
        max_workers_images: Number of images to download concurrently per profile (default: 5)
    """
    start_time = time.time()
    
    logger.info("="*70)
    logger.info("BACKSTAGE.COM COMPLETE SCRAPER (PARALLELIZED)")
    logger.info("="*70)
    logger.info(f"Max listing pages: {max_listing_pages if max_listing_pages else 'ALL'}")
    logger.info(f"Max profiles: {max_profiles if max_profiles else 'ALL'}")
    logger.info(f"Parallel profiles: {max_workers_profiles}")
    logger.info(f"Parallel images per profile: {max_workers_images}")
    logger.info(f"Delay between profiles: {delay_between_profiles}s")
    logger.info(f"Resume from file: {resume_from_file}")
    logger.info(f"Skip existing: {skip_existing}")
    logger.info("="*70)
    
    # ========================================
    # STEP 1: Get Profile URLs
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("STEP 1: SCRAPING PROFILE URLs FROM LISTING PAGES")
    logger.info("="*70)
    
    profiles: List[Tuple[str, str]] = []
    
    # Try to load existing profile list
    if resume_from_file and Path(profiles_file).exists():
        logger.info(f"Found existing profile list: {profiles_file}")
        profiles = load_profile_list(profiles_file)
        logger.info(f"Loaded {len(profiles)} profiles from file")
        
        if max_profiles:
            profiles = profiles[:max_profiles]
            logger.info(f"Limited to first {max_profiles} profiles")
    else:
        # Scrape listing pages
        logger.info("Scraping listing pages...")
        profiles = scrape_all_listing_pages(
            base_url="https://www.backstage.com/talent/",
            max_pages=max_listing_pages,
            rate_limit=2.0
        )
        
        if not profiles:
            logger.error("No profiles found! Exiting.")
            return
        
        # Save profile list
        save_profile_list(profiles, profiles_file)
        
        # Limit if specified
        if max_profiles:
            profiles = profiles[:max_profiles]
            logger.info(f"Limited to first {max_profiles} profiles")
    
    total_profiles = len(profiles)
    logger.success(f"Total profiles to process: {total_profiles}")
    
    # ========================================
    # STEP 2: Download Images from Each Profile
    # ========================================
    logger.info("\n" + "="*70)
    logger.info("STEP 2: DOWNLOADING IMAGES FROM PROFILES")
    logger.info("="*70)
    
    stats = {
        'total': total_profiles,
        'processed': 0,
        'skipped': 0,
        'successful': 0,
        'failed': 0,
        'failed_profiles': []
    }
    
    # Process profiles in parallel
    stats_lock = threading.Lock()
    
    logger.info(f"Processing {total_profiles} profiles with {max_workers_profiles} workers...")
    logger.info("Progress bar will show below:\n")
    
    # Use tqdm with file=sys.stderr to avoid conflicts with logger
    with tqdm(
        total=total_profiles,
        desc="Processing profiles",
        unit="profile",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
        file=sys.stderr,  # Write to stderr so it doesn't conflict with logger
        dynamic_ncols=True  # Adjust to terminal width
    ) as pbar:
        
        # Use ThreadPoolExecutor to process profiles in parallel
        with ThreadPoolExecutor(max_workers=max_workers_profiles) as executor:
            # Submit all profile processing tasks
            future_to_profile = {
                executor.submit(
                    process_single_profile_parallel,
                    profile_url,
                    actor_name,
                    skip_existing,
                    max_workers_images,
                    stats_lock,
                    stats
                ): (profile_url, actor_name)
                for profile_url, actor_name in profiles
            }
            
            # Process completed tasks as they finish
            try:
                for future in as_completed(future_to_profile):
                    profile_url, actor_name = future_to_profile[future]
                    try:
                        success, message = future.result()
                        if success:
                            logger.debug(message)
                        else:
                            logger.warning(message)
                    except Exception as e:
                        logger.error(f"Exception processing {actor_name}: {e}")
                        with stats_lock:
                            stats['failed'] += 1
                            stats['failed_profiles'].append((profile_url, actor_name))
                    
                    # Update progress bar
                    pbar.update(1)
                    
            except KeyboardInterrupt:
                logger.warning("\nInterrupted by user")
                logger.info("Cancelling remaining tasks...")
                # Cancel remaining futures
                for future in future_to_profile:
                    future.cancel()
                logger.info("Progress saved. You can resume by running again.")
    
    # ========================================
    # FINAL SUMMARY
    # ========================================
    duration = time.time() - start_time
    
    logger.info("\n" + "="*70)
    logger.info("SCRAPING COMPLETE - FINAL SUMMARY")
    logger.info("="*70)
    logger.success(f"Total profiles: {stats['total']}")
    logger.info(f"Processed: {stats['processed']}")
    logger.info(f"Skipped (existing): {stats['skipped']}")
    logger.success(f"Successful: {stats['successful']}")
    
    if stats['failed'] > 0:
        logger.error(f"Failed: {stats['failed']}")
        logger.info("Failed profiles:")
        for url, name in stats['failed_profiles']:
            logger.info(f"  - {name}: {url}")
    
    logger.info(f"Total time: {duration/60:.1f} minutes ({duration:.1f} seconds)")
    if stats['processed'] > 0:
        logger.info(f"Average time per profile: {duration/stats['processed']:.1f}s")
    
    logger.info(f"Profile list saved to: {profiles_file}")
    logger.info("="*70)


def scrape_single_profile(profile_url: str, actor_name: str) -> None:
    """
    Convenience function to scrape a single profile.
    
    Args:
        profile_url: URL of the profile page
        actor_name: Name of the actor (for folder naming)
    """
    logger.info("="*70)
    logger.info("SINGLE PROFILE SCRAPER")
    logger.info("="*70)
    
    try:
        scrape_and_download_profile(profile_url, actor_name)
        logger.success("Profile scraping completed successfully!")
    except Exception as e:
        logger.error(f"Failed to scrape profile: {e}")
        logger.exception("Full traceback:")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Backstage.com Complete Scraper - Scrapes listing pages and downloads images from profiles"
    )
    
    parser.add_argument(
        '--max-listing-pages',
        type=int,
        default=None,
        help='Maximum listing pages to scrape (default: all pages)'
    )
    
    parser.add_argument(
        '--max-profiles',
        type=int,
        default=None,
        help='Maximum profiles to process (default: all profiles)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between profiles in seconds (default: 2.0, not used in parallel mode)'
    )
    
    parser.add_argument(
        '--workers-profiles',
        type=int,
        default=3,
        help='Number of profiles to process concurrently (default: 3)'
    )
    
    parser.add_argument(
        '--workers-images',
        type=int,
        default=5,
        help='Number of images to download concurrently per profile (default: 5)'
    )
    
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Do not resume from existing profile list file'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Do not skip profiles that already have images'
    )
    
    parser.add_argument(
        '--profiles-file',
        type=str,
        default='all_profiles.txt',
        help='File to save/load profile list (default: all_profiles.txt)'
    )
    
    parser.add_argument(
        '--single',
        action='store_true',
        help='Scrape a single profile (requires --url and --name)'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='Profile URL (for single profile mode)'
    )
    
    parser.add_argument(
        '--name',
        type=str,
        help='Actor name (for single profile mode)'
    )
    
    args = parser.parse_args()
    
    # Single profile mode
    if args.single:
        if not args.url or not args.name:
            logger.error("Single profile mode requires --url and --name")
            sys.exit(1)
        scrape_single_profile(args.url, args.name)
    else:
        # Full scraper mode
        scrape_all_profiles(
            max_listing_pages=args.max_listing_pages,
            max_profiles=args.max_profiles,
            delay_between_profiles=args.delay,
            resume_from_file=not args.no_resume,
            skip_existing=not args.no_skip_existing,
            profiles_file=args.profiles_file,
            max_workers_profiles=args.workers_profiles,
            max_workers_images=args.workers_images
        )

