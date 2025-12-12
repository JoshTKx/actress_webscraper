# Worker Configuration Benchmark Guide

## Overview

The benchmark script tests different combinations of profile and image workers to find the optimal balance between speed and server load.

## Running the Benchmark

```bash
# Quick test with 3 profiles (recommended to start)
python src/benchmark_workers.py --test-profiles 3

# More thorough test with 5 profiles
python src/benchmark_workers.py --test-profiles 5

# Custom profile list
python src/benchmark_workers.py --test-profiles 3 --profiles-file custom_profiles.txt
```

## What It Tests

The benchmark tests these configurations:

1. **Sequential (baseline)**: 1 profile worker, 1 image worker
2. **1 profile, 3 images**: 1 profile worker, 3 image workers
3. **1 profile, 5 images**: 1 profile worker, 5 image workers
4. **1 profile, 10 images**: 1 profile worker, 10 image workers
5. **2 profiles, 3 images**: 2 profile workers, 3 image workers
6. **2 profiles, 5 images**: 2 profile workers, 5 image workers
7. **2 profiles, 10 images**: 2 profile workers, 10 image workers
8. **3 profiles, 3 images**: 3 profile workers, 3 image workers
9. **3 profiles, 5 images**: 3 profile workers, 5 image workers
10. **3 profiles, 10 images**: 3 profile workers, 10 image workers
11. **5 profiles, 5 images**: 5 profile workers, 5 image workers
12. **5 profiles, 10 images**: 5 profile workers, 10 image workers

## Metrics Tracked

- **Time**: Total duration of the test
- **Profiles**: Successfully processed profiles
- **Images**: Successfully downloaded images
- **Images/sec**: Throughput (images per second)
- **Rate Limits**: Number of rate limit errors (429, "too many requests")
- **Errors**: Number of other errors

## Interpreting Results

### Best Configuration Criteria

1. **Highest images/second** - Fastest throughput
2. **Zero rate limits** - No server overload
3. **Zero errors** - Reliable operation
4. **Good success rate** - Most images downloaded successfully

### What to Look For

- **Rate Limits > 0**: Configuration is too aggressive, reduce workers
- **Errors > 0**: May indicate network issues or server problems
- **Low images/sec**: Configuration is too conservative, can increase workers
- **High images/sec with no rate limits**: Optimal configuration!

## Recommendations

The benchmark will provide:

1. **Recommended Configuration**: Best balance of speed and reliability
2. **Conservative Configuration**: Safer option for long-running scrapes

## Example Output

```
BENCHMARK RESULTS
======================================================================
Config          Time       Profiles     Images       Img/sec    Rate Limits  Errors
----------------------------------------------------------------------------------
3p-5i          45.2s      3/3          30/30        0.66       0            0
2p-5i          52.1s      3/3          30/30        0.58       0            0
2p-3i          58.3s      3/3          30/30        0.51       0            0
1p-5i          65.4s      3/3          30/30        0.46       0            0
5p-10i         38.9s      3/3          28/30        0.72       2            1
...

RECOMMENDATIONS
======================================================================
Recommended configuration: 3 profile workers, 5 image workers
  - Images per second: 0.66
  - No rate limits hit
  - No errors

Conservative recommendation: 2 profile workers, 3 image workers
  - Safer for long-running scrapes
  - Images per second: 0.51
```

## Using Results

After running the benchmark, use the recommended configuration:

```bash
# Use recommended settings
python src/main_scraper.py \
  --workers-profiles 3 \
  --workers-images 5 \
  --max-profiles 50

# Or use conservative settings for long scrapes
python src/main_scraper.py \
  --workers-profiles 2 \
  --workers-images 3
```

## Notes

- Benchmark uses only 10 images per profile for speed
- Tests run sequentially with 5-second delays between tests
- Results may vary based on network conditions and server load
- Re-run benchmark periodically as server conditions change
- Clean up benchmark test files: `rm -rf data/actors/benchmark_*`

## Troubleshooting

**Benchmark fails immediately**: 
- Check internet connection
- Verify profile list file exists
- Ensure CloudScraper is working

**All configurations show rate limits**:
- Server may be under heavy load
- Try again later
- Use more conservative settings

**Very slow results**:
- Network may be slow
- Server may be throttling
- Consider running at different time


