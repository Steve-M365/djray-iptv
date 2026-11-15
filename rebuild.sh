#!/bin/bash
# Rebuild the catalog. Publishing is handled by .github/workflows/rebuild.yml;
# run this locally to refresh output/ before inspecting or serving it.
set -euo pipefail
cd "$(dirname "$0")"

echo "== DJRay IPTV rebuild =="
python3 build.py "$@"
echo
echo "Outputs are in ./output (master.m3u, sources/, presets/, epg.xml.gz)."