#!/bin/bash
# DJRay IPTV - Weekly playlist rebuild
# Run: python3 normalize_m3u_v2.py
# Commits and pushes changes automatically

set -e
cd "$(dirname "$0")"

echo "$(date): Starting DJRay IPTV rebuild..."

# Run normalizer
python3 normalize_m3u_v2.py

# Check if there are changes
if git diff --quiet && git diff --cached --quiet; then
    echo "$(date): No changes detected"
    exit 0
fi

# Commit and push
git add output/
git commit -m "auto: weekly playlist rebuild $(date +%Y-%m-%d)"
git push origin master

echo "$(date): Rebuild complete and pushed"
