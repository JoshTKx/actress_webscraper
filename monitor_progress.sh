#!/bin/bash
# Monitor scraper progress

echo "Monitoring scraper progress..."
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    clear
    echo "=========================================="
    echo "SCRAPER PROGRESS MONITOR"
    echo "=========================================="
    echo ""
    
    # Check if log exists
    if [ -f "scraper_run.log" ]; then
        echo "=== Recent Log Output ==="
        tail -20 scraper_run.log
        echo ""
    else
        echo "Log file not found yet..."
    fi
    
    # Check profile count
    if [ -f "all_profiles.txt" ]; then
        PROFILE_COUNT=$(grep -c "^https://" all_profiles.txt 2>/dev/null || echo "0")
        echo "=== Profile Statistics ==="
        echo "Total profiles found: $PROFILE_COUNT"
        echo ""
    fi
    
    # Check downloaded images
    if [ -d "data/actors" ]; then
        ACTOR_COUNT=$(find data/actors -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
        IMAGE_COUNT=$(find data/actors -name "image_*.jpg" -o -name "image_*.png" -o -name "image_*.jpeg" | wc -l | tr -d ' ')
        echo "=== Download Statistics ==="
        echo "Actors processed: $ACTOR_COUNT"
        echo "Total images downloaded: $IMAGE_COUNT"
        echo ""
    fi
    
    # Check process
    if pgrep -f "main_scraper.py" > /dev/null; then
        echo "=== Status ==="
        echo "Scraper is RUNNING"
    else
        echo "=== Status ==="
        echo "Scraper is NOT RUNNING"
    fi
    
    echo ""
    echo "Refreshing in 5 seconds... (Ctrl+C to stop)"
    sleep 5
done


