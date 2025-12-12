#!/usr/bin/env python3
"""
Quick test to compare 5, 10, and 20 image workers with 5 profile workers.
"""

import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
import threading

sys.path.insert(0, 'src')

from listing_scraper import load_profile_list
from profile_scraper import scrape_profile, download_image, config as profile_config
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

def test_image_workers(image_workers: int, test_profiles: list, test_name: str):
    """Test a specific number of image workers."""
    logger.info(f"\n{'='*70}")
    logger.info(f"Testing: {test_name}")
    logger.info(f"Image workers: {image_workers}")
    logger.info(f"{'='*70}")
    
    start_time = time.time()
    total_images = 0
    successful = 0
    failed = 0
    rate_limits = 0
    
    # Test with first profile that has images
    for profile_url, actor_name in test_profiles[:1]:
        try:
            # Scrape profile
            image_urls = scrape_profile(profile_url)
            if not image_urls:
                logger.warning(f"No images for {actor_name}, skipping")
                continue
            
            # Limit to 20 images for testing
            test_images = image_urls[:20]
            total_images = len(test_images)
            
            # Create test directory
            output_dir = profile_config.output_dir / f"test_{image_workers}workers"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            def download_img(args):
                idx, img_url = args
                extension = '.jpg'
                url_lower = img_url.lower()
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    if ext in url_lower:
                        extension = ext
                        break
                
                filename = f"test_{idx:03d}{extension}"
                save_path = output_dir / filename
                
                try:
                    if download_image(img_url, save_path):
                        return True, None
                    return False, None
                except Exception as e:
                    error_msg = str(e).lower()
                    if '429' in error_msg or 'rate limit' in error_msg:
                        return False, 'rate_limit'
                    return False, str(e)
            
            # Download with specified worker count
            with ThreadPoolExecutor(max_workers=image_workers) as executor:
                image_args = [(idx, url) for idx, url in enumerate(test_images, start=1)]
                results = list(executor.map(download_img, image_args))
            
            successful = sum(1 for r, _ in results if r)
            failed = len(results) - successful
            rate_limits = sum(1 for _, err in results if err == 'rate_limit')
            
            break  # Only test first profile
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    duration = time.time() - start_time
    images_per_sec = successful / duration if duration > 0 else 0
    
    return {
        'image_workers': image_workers,
        'total_images': total_images,
        'successful': successful,
        'failed': failed,
        'rate_limits': rate_limits,
        'duration': duration,
        'images_per_sec': images_per_sec
    }

if __name__ == "__main__":
    # Load test profiles
    profiles = load_profile_list("all_profiles.txt")
    if not profiles:
        logger.error("No profiles found!")
        sys.exit(1)
    
    logger.info(f"Testing with {len(profiles)} available profiles")
    logger.info("Testing different image worker counts with 5 profile workers...")
    
    # Test configurations
    configs = [
        (5, "5 image workers (current)"),
        (10, "10 image workers"),
        (20, "20 image workers"),
    ]
    
    results = []
    
    for image_workers, name in configs:
        try:
            result = test_image_workers(image_workers, profiles, name)
            if result:
                results.append(result)
            time.sleep(3)  # Small delay between tests
        except Exception as e:
            logger.error(f"Test failed for {name}: {e}")
    
    # Print results
    logger.info("\n" + "="*70)
    logger.info("RESULTS")
    logger.info("="*70)
    logger.info(f"{'Workers':<10} {'Images/sec':<12} {'Success':<10} {'Rate Limits':<12}")
    logger.info("-"*70)
    
    for r in sorted(results, key=lambda x: x['images_per_sec'], reverse=True):
        logger.info(f"{r['image_workers']:<10} {r['images_per_sec']:<12.2f} {r['successful']}/{r['total_images']:<6} {r['rate_limits']:<12}")
    
    # Recommendation
    best = max(results, key=lambda x: x['images_per_sec'])
    if best['rate_limits'] == 0:
        logger.info(f"\n✓ Recommended: {best['image_workers']} image workers")
        logger.info(f"  - {best['images_per_sec']:.2f} images/second")
        logger.info(f"  - No rate limits")
    else:
        # Find best without rate limits
        best_safe = next((r for r in sorted(results, key=lambda x: x['images_per_sec'], reverse=True) if r['rate_limits'] == 0), None)
        if best_safe:
            logger.info(f"\n✓ Recommended: {best_safe['image_workers']} image workers (safe)")
            logger.info(f"  - {best_safe['images_per_sec']:.2f} images/second")
        else:
            logger.warning(f"\n⚠ All configs hit rate limits. Use conservative: 5 image workers")


