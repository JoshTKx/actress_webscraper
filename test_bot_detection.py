#!/usr/bin/env python3
"""
Backstage.com Bot Detection Test
Tests different approaches to determine what's needed to bypass bot protection.
"""

import time
import httpx
from typing import Dict, Tuple

# Test URLs
BASE_URL = "https://www.backstage.com"
TALENT_URL = "https://www.backstage.com/talent/"
# Using a generic profile URL pattern - adjust if needed
PROFILE_URL = "https://www.backstage.com/talent/"

def test_basic_request() -> Tuple[bool, Dict]:
    """
    Test 1: Basic request with no special headers
    This will likely fail if there's any bot protection.
    """
    print("\n" + "="*60)
    print("TEST 1: Basic Request (No Headers)")
    print("="*60)
    
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(TALENT_URL)
            
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'url': str(response.url)
            }
            
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Final URL: {response.url}")
            
            # Check for common bot protection indicators
            if response.status_code == 403:
                print("ERROR BLOCKED: Got 403 Forbidden")
                return False, result
            elif response.status_code == 200:
                # Check if content looks like a real page or a challenge page
                content = response.text[:500].lower()
                if any(keyword in content for keyword in ['cloudflare', 'challenge', 'captcha', 'access denied']):
                    print("WARNING  SUSPICIOUS: Got 200 but page might be a challenge")
                    return False, result
                else:
                    print("SUCCESS SUCCESS: Got 200 with real content")
                    return True, result
            else:
                print(f"WARNING  UNEXPECTED: Status {response.status_code}")
                return False, result
                
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_browser_headers() -> Tuple[bool, Dict]:
    """
    Test 2: Request with browser-like headers
    Mimics a real browser request.
    """
    print("\n" + "="*60)
    print("TEST 2: Browser Headers")
    print("="*60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            response = client.get(TALENT_URL)
            
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'url': str(response.url)
            }
            
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Final URL: {response.url}")
            
            if response.status_code == 403:
                print("ERROR BLOCKED: Still got 403 even with browser headers")
                return False, result
            elif response.status_code == 200:
                content = response.text[:500].lower()
                if any(keyword in content for keyword in ['cloudflare', 'challenge', 'captcha', 'access denied']):
                    print("WARNING  SUSPICIOUS: Got 200 but page might be a challenge")
                    return False, result
                else:
                    print("SUCCESS SUCCESS: Got 200 with real content using browser headers")
                    return True, result
            else:
                print(f"WARNING  UNEXPECTED: Status {response.status_code}")
                return False, result
                
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_session_cookies() -> Tuple[bool, Dict]:
    """
    Test 3: Session management with cookies
    First visits homepage to get cookies, then accesses talent page.
    """
    print("\n" + "="*60)
    print("TEST 3: Session + Cookies")
    print("="*60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # Step 1: Visit homepage to establish session
            print("Step 1: Visiting homepage to get cookies...")
            home_response = client.get(BASE_URL)
            print(f"  Homepage status: {home_response.status_code}")
            print(f"  Cookies received: {len(client.cookies)}")
            
            # Small delay to mimic human behavior
            time.sleep(1)
            
            # Step 2: Now try to access talent page with cookies
            print("Step 2: Accessing talent page with session cookies...")
            response = client.get(TALENT_URL)
            
            result = {
                'status_code': response.status_code,
                'homepage_status': home_response.status_code,
                'cookies_count': len(client.cookies),
                'content_length': len(response.content),
                'url': str(response.url)
            }
            
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Cookies in session: {len(client.cookies)}")
            
            if response.status_code == 403:
                print("ERROR BLOCKED: Still got 403 even with session cookies")
                return False, result
            elif response.status_code == 200:
                content = response.text[:500].lower()
                if any(keyword in content for keyword in ['cloudflare', 'challenge', 'captcha', 'access denied']):
                    print("WARNING  SUSPICIOUS: Got 200 but page might be a challenge")
                    return False, result
                else:
                    print("SUCCESS SUCCESS: Got 200 with session management")
                    return True, result
            else:
                print(f"WARNING  UNEXPECTED: Status {response.status_code}")
                return False, result
                
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def test_profile_page() -> Tuple[bool, Dict]:
    """
    Test 4: Direct access to a profile page
    Sometimes profile pages have different protection than listing pages.
    """
    print("\n" + "="*60)
    print("TEST 4: Profile Page Access")
    print("="*60)
    
    # Try accessing a generic profile URL
    # Note: This might need adjustment based on actual Backstage URL structure
    profile_url = "https://www.backstage.com/talent/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.backstage.com/',
        'Connection': 'keep-alive',
    }
    
    try:
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # First visit homepage
            client.get(BASE_URL)
            time.sleep(1)
            
            # Then try profile page
            response = client.get(profile_url)
            
            result = {
                'status_code': response.status_code,
                'content_length': len(response.content),
                'url': str(response.url)
            }
            
            print(f"Status Code: {response.status_code}")
            print(f"Content Length: {len(response.content)} bytes")
            print(f"Final URL: {response.url}")
            
            if response.status_code == 403:
                print("ERROR BLOCKED: Profile page also blocked")
                return False, result
            elif response.status_code == 200:
                content = response.text[:500].lower()
                if any(keyword in content for keyword in ['cloudflare', 'challenge', 'captcha', 'access denied']):
                    print("WARNING  SUSPICIOUS: Got 200 but might be challenge page")
                    return False, result
                else:
                    print("SUCCESS SUCCESS: Profile page accessible")
                    return True, result
            else:
                print(f"WARNING  UNEXPECTED: Status {response.status_code}")
                return False, result
                
    except Exception as e:
        print(f"ERROR ERROR: {e}")
        return False, {'error': str(e)}

def analyze_results(results: Dict[str, Tuple[bool, Dict]]) -> None:
    """Analyze test results and provide recommendations."""
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    passed = []
    failed = []
    
    for test_name, (success, details) in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed.append(test_name)
        else:
            failed.append(test_name)
    
    print("\n" + "="*60)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*60)
    
    # Check which tests passed
    all_passed = all(success for success, _ in results.values())
    browser_headers_worked = results['test_browser_headers'][0]
    session_worked = results['test_session_cookies'][0]
    
    if all_passed:  # All passed
        print("\nSUCCESS All tests passed! Backstage.com is accessible with basic requests.")
        print("\nRecommended approach:")
        print("  - Use browser-like headers")
        print("  - Implement rate limiting (2+ second delays)")
        print("  - No special session management needed")
        
    elif browser_headers_worked:  # Browser headers worked
        print("\nSUCCESS Browser headers are sufficient!")
        print("\nRecommended approach:")
        print("  - Always include full browser headers (User-Agent, Accept, etc.)")
        print("  - Use session management for consistency")
        print("  - Implement rate limiting (2+ second delays)")
        print("  - No need for browser automation")
        
    elif results['test_session_cookies'][0]:  # Session worked
        print("\nSUCCESS Session management is required!")
        print("\nRecommended approach:")
        print("  - Use httpx.Client() with persistent session")
        print("  - Visit homepage first to establish session")
        print("  - Maintain cookies across requests")
        print("  - Include full browser headers")
        print("  - Implement rate limiting")
        
    else:  # All failed
        print("\nERROR All tests failed. Backstage.com has strong bot protection.")
        print("\nPossible reasons:")
        print("  - Cloudflare or similar protection service")
        print("  - JavaScript-based challenge (requires browser rendering)")
        print("  - IP-based rate limiting or blocking")
        print("  - Requires authentication/login")
        
        print("\nRecommended approaches (in order of complexity):")
        print("  1. Try rotating User-Agents and adding more headers")
        print("  2. Use browser automation (Selenium/Playwright) if JS is required")
        print("  3. Check if API endpoints exist (often less protected)")
        print("  4. Consider using a proxy service")
        print("  5. Contact Backstage.com for official API access")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("1. Review the detailed results above")
    print("2. Choose the recommended approach based on what worked")
    print("3. Build your scraper using the successful method")
    print("4. Always implement rate limiting and respect robots.txt")
    print("5. Test with small batches first before full scraping")

def main():
    """Run all bot detection tests."""
    print("="*60)
    print("BACKSTAGE.COM BOT DETECTION TEST")
    print("="*60)
    print("\nThis script tests different approaches to access Backstage.com")
    print("to determine what level of bot protection exists.")
    print("\nWARNING  Note: This is for educational purposes only.")
    print("    Always respect robots.txt and terms of service.")
    print("\nStarting tests...")
    
    results = {}
    
    # Run all tests with delays between them
    results['test_basic_request'] = test_basic_request()
    time.sleep(2)  # Be polite between tests
    
    results['test_browser_headers'] = test_browser_headers()
    time.sleep(2)
    
    results['test_session_cookies'] = test_session_cookies()
    time.sleep(2)
    
    results['test_profile_page'] = test_profile_page()
    
    # Analyze and provide recommendations
    analyze_results(results)

if __name__ == "__main__":
    main()

