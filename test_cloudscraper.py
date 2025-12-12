#!/usr/bin/env python3
"""
CloudScraper Test Script
Tests cloudscraper against Backstage.com to see if it can bypass Cloudflare protection.
"""

import cloudscraper
import time
from typing import Dict, Tuple

# URLs to test
URLS_TO_TEST = [
    ("Homepage", "https://www.backstage.com/"),
    ("Talent Directory", "https://www.backstage.com/talent/"),
    ("Sample Profile", "https://www.backstage.com/tal/jonathancantor/"),
]

def test_basic_scraper(url: str, name: str) -> Tuple[bool, Dict]:
    """
    Test 1: Basic cloudscraper (default configuration)
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name} - Basic CloudScraper")
    print(f"{'='*60}")
    print(f"URL: {url}")
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=15)
        
        # Better detection: Look for actual Cloudflare challenge page indicators
        content_lower = response.text.lower()
        is_cloudflare_challenge = (
            'attention required' in content_lower and 'cloudflare' in content_lower
        ) or (
            'sorry, you have been blocked' in content_lower
        ) or (
            'cf-error-details' in content_lower and len(response.content) < 20000
        )
        
        # Check for real content indicators
        has_real_content = (
            'talent' in content_lower and ('directory' in content_lower or 'search' in content_lower)
        ) or (
            'actor' in content_lower or 'actress' in content_lower
        ) or (
            'portfolio' in content_lower and 'image' in content_lower
        )
        
        result = {
            'status_code': response.status_code,
            'content_length': len(response.content),
            'url': str(response.url),
            'has_backstage': 'backstage' in content_lower,
            'is_cloudflare_challenge': is_cloudflare_challenge,
            'has_real_content': has_real_content
        }
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content):,} bytes")
        print(f"Final URL: {response.url}")
        print(f"Contains 'backstage': {result['has_backstage']}")
        print(f"Cloudflare challenge page: {is_cloudflare_challenge}")
        print(f"Real content detected: {has_real_content}")
        
        # Determine success
        if response.status_code == 200 and has_real_content and not is_cloudflare_challenge:
            print("SUCCESS SUCCESS: Got real content!")
            return True, result
        elif response.status_code == 200 and is_cloudflare_challenge:
            print("WARNING  PARTIAL: Got 200 but still blocked by Cloudflare")
            return False, result
        elif response.status_code == 403:
            print("ERROR BLOCKED: Got 403 Forbidden")
            return False, result
        else:
            print(f"WARNING  UNEXPECTED: Status {response.status_code}")
            return False, result
            
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_with_delay(url: str, name: str, delay: float = 2.0) -> Tuple[bool, Dict]:
    """
    Test 2: CloudScraper with delay (mimics human behavior)
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name} - CloudScraper with {delay}s delay")
    print(f"{'='*60}")
    print(f"URL: {url}")
    
    try:
        time.sleep(delay)  # Delay before request
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=15)
        
        content_lower = response.text.lower()
        is_cloudflare_challenge = (
            'attention required' in content_lower and 'cloudflare' in content_lower
        ) or 'sorry, you have been blocked' in content_lower
        has_real_content = 'talent' in content_lower and ('directory' in content_lower or 'search' in content_lower)
        
        result = {
            'status_code': response.status_code,
            'content_length': len(response.content),
            'url': str(response.url),
            'has_backstage': 'backstage' in content_lower,
            'is_cloudflare_challenge': is_cloudflare_challenge,
            'has_real_content': has_real_content
        }
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content):,} bytes")
        print(f"Real content detected: {has_real_content}")
        
        if response.status_code == 200 and has_real_content and not is_cloudflare_challenge:
            print("SUCCESS SUCCESS: Got real content with delay!")
            return True, result
        else:
            print("ERROR Still blocked or invalid response")
            return False, result
            
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_with_browser_param(url: str, name: str) -> Tuple[bool, Dict]:
    """
    Test 3: CloudScraper with browser parameter (specifies browser to mimic)
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name} - CloudScraper with browser='chrome'")
    print(f"{'='*60}")
    print(f"URL: {url}")
    
    try:
        scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'darwin',
            'desktop': True
        })
        response = scraper.get(url, timeout=15)
        
        content_lower = response.text.lower()
        is_cloudflare_challenge = (
            'attention required' in content_lower and 'cloudflare' in content_lower
        ) or 'sorry, you have been blocked' in content_lower
        has_real_content = 'talent' in content_lower and ('directory' in content_lower or 'search' in content_lower)
        
        result = {
            'status_code': response.status_code,
            'content_length': len(response.content),
            'url': str(response.url),
            'has_backstage': 'backstage' in content_lower,
            'is_cloudflare_challenge': is_cloudflare_challenge,
            'has_real_content': has_real_content
        }
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content):,} bytes")
        print(f"Real content detected: {has_real_content}")
        
        if response.status_code == 200 and has_real_content and not is_cloudflare_challenge:
            print("SUCCESS SUCCESS: Got real content with browser param!")
            return True, result
        else:
            print("ERROR Still blocked or invalid response")
            return False, result
            
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_with_interpreter(url: str, name: str) -> Tuple[bool, Dict]:
    """
    Test 4: CloudScraper with interpreter parameter (uses Node.js for JS execution)
    Note: This requires nodejs to be installed
    """
    print(f"\n{'='*60}")
    print(f"TEST: {name} - CloudScraper with interpreter='nodejs'")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print("WARNING  Note: Requires Node.js to be installed")
    
    try:
        scraper = cloudscraper.create_scraper(interpreter='nodejs')
        response = scraper.get(url, timeout=20)  # Longer timeout for JS execution
        
        content_lower = response.text.lower()
        is_cloudflare_challenge = (
            'attention required' in content_lower and 'cloudflare' in content_lower
        ) or 'sorry, you have been blocked' in content_lower
        has_real_content = 'talent' in content_lower and ('directory' in content_lower or 'search' in content_lower)
        
        result = {
            'status_code': response.status_code,
            'content_length': len(response.content),
            'url': str(response.url),
            'has_backstage': 'backstage' in content_lower,
            'is_cloudflare_challenge': is_cloudflare_challenge,
            'has_real_content': has_real_content
        }
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content):,} bytes")
        print(f"Real content detected: {has_real_content}")
        
        if response.status_code == 200 and has_real_content and not is_cloudflare_challenge:
            print("SUCCESS SUCCESS: Got real content with Node.js interpreter!")
            return True, result
        else:
            print("ERROR Still blocked or invalid response")
            return False, result
            
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        print("   (Node.js might not be installed or configured)")
        return False, {'error': str(e)}

def analyze_results(all_results: Dict) -> None:
    """Analyze all test results and provide recommendations."""
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    # Count successes
    total_tests = 0
    successful_tests = 0
    successful_urls = set()
    
    for test_name, (success, details) in all_results.items():
        total_tests += 1
        if success:
            successful_tests += 1
            # Extract URL name from test name
            for url_name, _ in URLS_TO_TEST:
                if url_name in test_name:
                    successful_urls.add(url_name)
        
        status = "PASS" if success else "FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nSuccess Rate: {successful_tests}/{total_tests} tests passed")
    print(f"Successful URLs: {', '.join(successful_urls) if successful_urls else 'None'}")
    
    print("\n" + "="*60)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*60)
    
    if successful_tests == total_tests:
        print("\nOUTCOME A: CloudScraper Works Perfectly!")
        print("\nSUCCESS: All tests passed - CloudScraper can bypass Cloudflare protection")
        print("\nRecommended approach:")
        print("  1. Use cloudscraper.create_scraper() for all requests")
        print("  2. Add rate limiting (2+ second delays between requests)")
        print("  3. Implement proper error handling")
        print("  4. Test on a few profiles first before full scrape")
        print("\nSUCCESS: You can proceed with building your scraper using CloudScraper!")
        
    elif successful_tests > 0:
        print("\n OUTCOME C: Partial Success")
        print(f"\nWARNING: Some tests passed ({successful_tests}/{total_tests})")
        print(f"   Working URLs: {', '.join(successful_urls) if successful_urls else 'None'}")
        print("\nPossible reasons:")
        print("  - Some pages have different protection levels")
        print("  - Rate limiting might be needed")
        print("  - Some URLs might require authentication")
        print("\nRecommended approach:")
        print("  1. Use CloudScraper for pages that work")
        print("  2. Add delays between requests (3-5 seconds)")
        print("  3. Handle failures gracefully")
        print("  4. Consider using the working configuration")
        print("\nWARNING  Proceed with caution - test thoroughly before full scrape")
        
    else:
        print("\nOUTCOME B: CloudScraper Cannot Bypass Protection")
        print("\nERROR: All tests failed - CloudScraper cannot bypass modern Bot Management")
        print("\nThis means Backstage.com uses advanced Cloudflare Bot Management that")
        print("requires full browser automation to bypass.")
        print("\nYour options:")
        print("  1. Use Playwright/Puppeteer (browser automation)")
        print("     - More complex but most reliable")
        print("     - Requires browser installation")
        print("     - Slower but handles JavaScript challenges")
        print("\n  2. Try different approach:")
        print("     - Check for API endpoints")
        print("     - Use official Backstage API if available")
        print("     - Contact Backstage for data access")
        print("\n  3. Pivot to different data source")
        print("     - Find alternative sites with similar data")
        print("     - Use public datasets if available")
        print("\nERROR Cannot proceed with CloudScraper - need alternative approach")

def main():
    """Run all CloudScraper tests."""
    print("="*60)
    print("CLOUDSCRAPER TEST - BACKSTAGE.COM")
    print("="*60)
    print("\nTesting if CloudScraper can bypass Cloudflare Bot Management")
    print("This will test multiple URLs and configurations.")
    print("\nWARNING  Note: This is for educational purposes only.")
    print("    Always respect robots.txt and terms of service.")
    print("\nStarting tests...\n")
    
    all_results = {}
    
    # Test each URL with basic scraper first
    for url_name, url in URLS_TO_TEST:
        test_name = f"{url_name} - Basic"
        all_results[test_name] = test_basic_scraper(url, url_name)
        time.sleep(2)  # Be polite between tests
    
    # If basic works, test variations on the first successful URL
    # Find a URL that worked
    working_url = None
    working_name = None
    for url_name, url in URLS_TO_TEST:
        test_name = f"{url_name} - Basic"
        if test_name in all_results and all_results[test_name][0]:
            working_url = url
            working_name = url_name
            break
    
    # Test variations on working URL (or first URL if none worked)
    if working_url:
        test_url = working_url
        test_name = working_name
    else:
        test_url = URLS_TO_TEST[0][1]
        test_name = URLS_TO_TEST[0][0]
    
    print(f"\n{'='*60}")
    print("TESTING VARIATIONS")
    print(f"{'='*60}")
    print(f"Using: {test_name} ({test_url})")
    
    # Test with delay
    all_results[f"{test_name} - With Delay"] = test_with_delay(test_url, test_name)
    time.sleep(2)
    
    # Test with browser param
    all_results[f"{test_name} - Browser Param"] = test_with_browser_param(test_url, test_name)
    time.sleep(2)
    
    # Test with interpreter (might fail if Node.js not installed)
    all_results[f"{test_name} - Node.js Interpreter"] = test_with_interpreter(test_url, test_name)
    
    # Analyze results
    analyze_results(all_results)

if __name__ == "__main__":
    main()

