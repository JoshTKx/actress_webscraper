#!/usr/bin/env python3
"""
Benchmark script to find optimal worker configuration.
Tests different combinations of profile and image workers to find
the best balance between speed and server load.
"""

import sys
from pathlib import Path
import time
from typing import List, Tuple, Dict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from tqdm import tqdm

# Import our scrapers
from listing_scraper import load_profile_list
from profile_scraper import scrape_profile, download_image, config as profile_config

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

Path("logs").mkdir(exist_ok=True)
logger.add(
    "logs/benchmark_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


def test_configuration(
    profile_workers: int,
    image_workers: int,
    test_profiles: List[Tuple[str, str]],
    test_name: str
) -> Dict:
    """
    Test a specific worker configuration.
    
    Returns:
        Dictionary with performance metrics
    """
    logger.info("="*70)
    logger.info(f"Testing: {test_name}")
    logger.info(f"Profile workers: {profile_workers}, Image workers: {image_workers}")
    logger.info("="*70)
    
    stats = {
        'config': f"{profile_workers}p-{image_workers}i",
        'profile_workers': profile_workers,
        'image_workers': image_workers,
        'total_profiles': len(test_profiles),
        'start_time': time.time(),
        'successful_profiles': 0,
        'failed_profiles': 0,
        'total_images': 0,
        'successful_images': 0,
        'failed_images': 0,
        'errors': [],
        'rate_limit_hits': 0
    }
    
    stats_lock = threading.Lock()
    
    def process_profile(profile_url: str, actor_name: str) -> Tuple[bool, int, int, List[str], int]:
        """Process a single profile and return stats."""
        try:
            # Scrape profile
            image_urls = scrape_profile(profile_url)
            
            if not image_urls:
                return False, 0, 0, [], 0
            
            # Create output directory
            output_dir = profile_config.output_dir / f"benchmark_{actor_name}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download images in parallel
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
                    if '429' in error_msg or 'rate limit' in error_msg or 'too many' in error_msg:
                        return False, 'rate_limit'
                    return False, str(e)
            
            # Download with specified worker count
            with ThreadPoolExecutor(max_workers=image_workers) as executor:
                image_args = [(idx, url) for idx, url in enumerate(image_urls[:10], start=1)]  # Limit to 10 images for testing
                results = list(executor.map(download_img, image_args))
            
            successful = sum(1 for r, _ in results if r)
            failed = len(results) - successful
            rate_limits = sum(1 for _, err in results if err == 'rate_limit')
            errors = [err for _, err in results if err and err != 'rate_limit']
            
            return True, successful, failed, errors, rate_limits
            
        except Exception as e:
            error_msg = str(e).lower()
            if '429' in error_msg or 'rate limit' in error_msg:
                return False, 0, 0, [], 1
            return False, 0, 0, [str(e)], 0
    
    # Process profiles in parallel
    with ThreadPoolExecutor(max_workers=profile_workers) as executor:
        future_to_profile = {
            executor.submit(process_profile, url, name): (url, name)
            for url, name in test_profiles
        }
        
        for future in as_completed(future_to_profile):
            profile_url, actor_name = future_to_profile[future]
            try:
                success, img_success, img_failed, errors, rate_limits = future.result()
                
                with stats_lock:
                    if success:
                        stats['successful_profiles'] += 1
                        stats['total_images'] += (img_success + img_failed)
                        stats['successful_images'] += img_success
                        stats['failed_images'] += img_failed
                        stats['rate_limit_hits'] += rate_limits
                        if errors:
                            stats['errors'].extend(errors)
                    else:
                        stats['failed_profiles'] += 1
                        if errors:
                            stats['errors'].extend(errors)
                        if rate_limits:
                            stats['rate_limit_hits'] += rate_limits
                            
            except Exception as e:
                with stats_lock:
                    stats['failed_profiles'] += 1
                    stats['errors'].append(str(e))
    
    stats['duration'] = time.time() - stats['start_time']
    stats['images_per_second'] = stats['successful_images'] / stats['duration'] if stats['duration'] > 0 else 0
    stats['profiles_per_second'] = stats['successful_profiles'] / stats['duration'] if stats['duration'] > 0 else 0
    
    return stats


def run_benchmark(
    test_profiles_count: int = 5,
    profiles_file: str = "all_profiles.txt"
) -> None:
    """
    Run benchmark tests with different worker configurations.
    """
    logger.info("="*70)
    logger.info("WORKER CONFIGURATION BENCHMARK")
    logger.info("="*70)
    
    # Load test profiles
    all_profiles = load_profile_list(profiles_file)
    if not all_profiles:
        logger.error("No profiles found! Run listing scraper first.")
        return
    
    test_profiles = all_profiles[:test_profiles_count]
    logger.info(f"Using {len(test_profiles)} profiles for testing")
    logger.info("="*70)
    
    # Test configurations
    # Format: (profile_workers, image_workers, description)
    configurations = [
        (1, 1, "Sequential (baseline)"),
        (1, 3, "1 profile, 3 images"),
        (1, 5, "1 profile, 5 images"),
        (1, 10, "1 profile, 10 images"),
        (2, 3, "2 profiles, 3 images"),
        (2, 5, "2 profiles, 5 images"),
        (2, 10, "2 profiles, 10 images"),
        (3, 3, "3 profiles, 3 images"),
        (3, 5, "3 profiles, 5 images"),
        (3, 10, "3 profiles, 10 images"),
        (5, 5, "5 profiles, 5 images"),
        (5, 10, "5 profiles, 10 images"),
    ]
    
    results = []
    
    for profile_workers, image_workers, description in configurations:
        try:
            stats = test_configuration(
                profile_workers,
                image_workers,
                test_profiles,
                description
            )
            results.append(stats)
            
            # Small delay between tests to avoid carryover effects
            logger.info("Waiting 5 seconds before next test...")
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.warning("Benchmark interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in test {description}: {e}")
            continue
    
    # Print results summary
    print_results(results)


def print_results(results: List[Dict]) -> None:
    """Print benchmark results in a formatted table."""
    logger.info("\n" + "="*70)
    logger.info("BENCHMARK RESULTS")
    logger.info("="*70)
    
    if not results:
        logger.warning("No results to display")
        return
    
    # Sort by images per second (descending)
    results_sorted = sorted(results, key=lambda x: x['images_per_second'], reverse=True)
    
    # Print header
    header = f"{'Config':<15} {'Time':<10} {'Profiles':<12} {'Images':<12} {'Img/sec':<10} {'Rate Limits':<12} {'Errors':<8}"
    logger.info(header)
    logger.info("-" * 90)
    
    # Print each result
    for stats in results_sorted:
        config = stats['config']
        duration = f"{stats['duration']:.1f}s"
        profiles = f"{stats['successful_profiles']}/{stats['total_profiles']}"
        images = f"{stats['successful_images']}/{stats['total_images']}"
        img_per_sec = f"{stats['images_per_second']:.2f}"
        rate_limits = str(stats['rate_limit_hits'])
        errors = str(len(stats['errors']))
        
        row = f"{config:<15} {duration:<10} {profiles:<12} {images:<12} {img_per_sec:<10} {rate_limits:<12} {errors:<8}"
        logger.info(row)
    
    # Recommendations
    logger.info("\n" + "="*70)
    logger.info("RECOMMENDATIONS")
    logger.info("="*70)
    
    # Find best configuration (highest throughput, no rate limits, minimal errors)
    best = None
    for stats in results_sorted:
        if stats['rate_limit_hits'] == 0 and len(stats['errors']) == 0:
            best = stats
            break
    
    if best:
        logger.success(f"Recommended configuration: {best['profile_workers']} profile workers, {best['image_workers']} image workers")
        logger.info(f"  - Images per second: {best['images_per_second']:.2f}")
        logger.info(f"  - No rate limits hit")
        logger.info(f"  - No errors")
    else:
        # Find best with minimal rate limits
        best = min(results_sorted, key=lambda x: (x['rate_limit_hits'], -x['images_per_second']))
        logger.warning(f"Best available (some rate limits): {best['profile_workers']} profile workers, {best['image_workers']} image workers")
        logger.info(f"  - Images per second: {best['images_per_second']:.2f}")
        logger.info(f"  - Rate limits: {best['rate_limit_hits']}")
    
    # Conservative recommendation
    conservative = None
    for stats in results_sorted:
        if stats['profile_workers'] <= 2 and stats['image_workers'] <= 5 and stats['rate_limit_hits'] == 0:
            conservative = stats
            break
    
    if conservative:
        logger.info(f"\nConservative recommendation: {conservative['profile_workers']} profile workers, {conservative['image_workers']} image workers")
        logger.info(f"  - Safer for long-running scrapes")
        logger.info(f"  - Images per second: {conservative['images_per_second']:.2f}")
    
    logger.info("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Benchmark worker configurations to find optimal settings"
    )
    
    parser.add_argument(
        '--test-profiles',
        type=int,
        default=5,
        help='Number of profiles to test with (default: 5)'
    )
    
    parser.add_argument(
        '--profiles-file',
        type=str,
        default='all_profiles.txt',
        help='Profile list file (default: all_profiles.txt)'
    )
    
    args = parser.parse_args()
    
    run_benchmark(
        test_profiles_count=args.test_profiles,
        profiles_file=args.profiles_file
    )

