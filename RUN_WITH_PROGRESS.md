# Running with Progress Bars (tqdm)

## Current Status

The scraper **already uses tqdm** for progress tracking! You should see progress bars when running.

## How to See Progress Bars

### Option 1: Run Normally (Progress Bar Visible)

```bash
python src/main_scraper.py --workers-profiles 10 --workers-images 10
```

You'll see:
- **Profile progress bar**: Shows how many profiles have been processed
- **Image progress bars**: (Inside profile_scraper.py) Shows images downloading per profile

### Option 2: Run with Less Logging (Cleaner Progress)

If the progress bar is getting hidden by too much log output, you can:

```bash
# Run with INFO level (less verbose)
python src/main_scraper.py --workers-profiles 10 --workers-images 10 2>&1 | grep -v "DEBUG"
```

### Option 3: Run with Only Progress Bar (Minimal Output)

```bash
# Redirect logs to file, keep progress bar visible
python src/main_scraper.py --workers-profiles 10 --workers-images 10 2>scraper.log
```

The progress bar will show in terminal, logs go to file.

## What You'll See

```
Processing profiles: 45%|████▌     | 4523/10035 [2:15:30<2:45:20, 3.33profile/s]
```

This shows:
- **45%**: Percentage complete
- **4523/10035**: Profiles processed / Total profiles
- **2:15:30**: Time elapsed
- **<2:45:20**: Estimated time remaining
- **3.33profile/s**: Processing rate

## If Progress Bar Isn't Showing

1. **Check terminal**: Progress bars need a TTY (not piped output)
2. **Check tqdm installation**: `pip install tqdm`
3. **Run directly**: Don't pipe to files if you want to see progress

## Monitoring Progress

While the scraper runs, you can monitor in another terminal:

```bash
# Watch progress
tail -f logs/main_scraper_2025-12-12.log | grep -E "(Processing|Total|Successful)"

# Check how many actors processed
find data/actors -mindepth 1 -maxdepth 1 -type d | wc -l

# Check total images downloaded
find data/actors -name "image_*.jpg" -o -name "image_*.png" | wc -l
```

## Current Running Scraper

If your scraper is already running, the progress bar should be visible in the terminal where you started it. If you can't see it:

1. Check the terminal window where you ran the command
2. The progress bar updates as profiles complete
3. It might be mixed with log output - that's normal


