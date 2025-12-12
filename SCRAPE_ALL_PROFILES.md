# Scraping All Profiles

## Current Status

You currently have **150 profiles** because the initial test was run with `--max-pages 3`.

## How Many Profiles Are There?

The site likely has **hundreds or thousands** of profiles across many pages. The scraper can find all of them by continuing to increment page numbers until it hits an empty page.

## Scrape All Profiles

### Option 1: Use Main Scraper (Recommended)

This will scrape all listing pages and then download images:

```bash
# Scrape ALL listing pages (no limit)
python src/main_scraper.py --no-resume --max-listing-pages None

# Or just let it use existing profile list if you want to skip listing scrape
python src/main_scraper.py
```

### Option 2: Just Scrape Listing Pages

If you only want to update the profile list:

```bash
python -c "
from src.listing_scraper import scrape_all_listing_pages, save_profile_list
profiles = scrape_all_listing_pages()  # No max_pages = all pages
save_profile_list(profiles, 'all_profiles.txt')
print(f'Scraped {len(profiles)} total profiles!')
"
```

### Option 3: Use Listing Scraper Directly

```python
from src.listing_scraper import scrape_all_listing_pages, save_profile_list

# Scrape ALL pages (no limit)
profiles = scrape_all_listing_pages(max_pages=None)

# Save to file
save_profile_list(profiles, "all_profiles.txt")

print(f"Total profiles: {len(profiles)}")
```

## How It Works

The scraper will:

1. Start at page 1 (`/talent/`)
2. Extract ~50 profiles per page
3. Find next page URL (`?page=2`, `?page=3`, etc.)
4. Continue until:
   - No profiles found on a page (end of pagination)
   - No next page URL found
   - Error occurs

## Time Estimate

- **~50 profiles per page**
- **~2 seconds between pages** (rate limiting)
- **Example**: 200 pages = ~400 seconds = ~6.7 minutes just for listing pages

## Important Notes

1. **Rate Limiting**: The scraper waits 2 seconds between pages to be polite
2. **Resume Support**: If interrupted, you can resume - it saves progress to `all_profiles.txt`
3. **No Max Pages**: By default, `max_pages=None` means it will scrape ALL pages
4. **Progress Tracking**: Watch the logs to see progress

## Example Output

```
Page 1: https://www.backstage.com/talent/
Page 1: +50 profiles (Total: 50)

Page 2: https://www.backstage.com/talent/?page=2
Page 2: +50 profiles (Total: 100)

...

Page 200: https://www.backstage.com/talent/?page=200
Page 200: +50 profiles (Total: 10,000)

No more pages found - reached the end!
```

## After Scraping All Profiles

Once you have the complete profile list, you can:

1. **Download images from all profiles**:

   ```bash
   python src/main_scraper.py --max-profiles None
   ```

2. **Download images in batches**:

   ```bash
   python src/main_scraper.py --max-profiles 100
   ```

3. **Use optimal worker settings** (from benchmark):
   ```bash
   python src/main_scraper.py \
     --workers-profiles 5 \
     --workers-images 5 \
     --max-profiles None
   ```

