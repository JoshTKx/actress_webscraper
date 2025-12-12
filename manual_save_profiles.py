#!/usr/bin/env python3
"""
Manual script to save profiles from a running scraper.
This reads the log file to extract the current profile count.
Note: This is a workaround - the file will auto-save when scraper finishes.
"""

import sys
from pathlib import Path
import re
from datetime import datetime

# The scraper saves at the end, but if you want to check progress:
# The file will be updated when:
# 1. The scraper finishes (automatic final save)
# 2. Every 10 pages (if using new code with incremental saves)
# 3. When you restart the scraper with the new code

print("="*70)
print("PROFILE FILE STATUS")
print("="*70)

profile_file = Path("all_profiles.txt")
if profile_file.exists():
    with open(profile_file, 'r') as f:
        lines = [l for l in f if l.strip() and not l.startswith('#')]
        current_count = len(lines)
    
    print(f"Current profiles in file: {current_count}")
    
    # Check log for actual progress
    log_file = Path("logs/main_scraper_2025-12-12.log")
    if log_file.exists():
        with open(log_file, 'r') as f:
            content = f.read()
            # Find latest page count
            matches = re.findall(r'Page (\d+):.*Total: (\d+)', content)
            if matches:
                latest_page, latest_total = matches[-1]
                print(f"Latest in log: Page {latest_page}, Total: {latest_total} profiles")
                print(f"\nDifference: {int(latest_total) - current_count} profiles not yet saved")
                print("\nThe file will be updated when:")
                print("  - Scraper finishes (automatic save)")
                print("  - Or every 10 pages (if using new code)")
else:
    print("Profile file not found!")

print("="*70)


