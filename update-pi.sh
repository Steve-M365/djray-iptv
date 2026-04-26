#!/bin/bash
# Quick update: Regenerate and copy files to Raspberry Pi
# Run this from your Mac in the apsattv-iptv directory

set -e

cd /Users/steve/scripts/apsattv-iptv

echo "=== Regenerating playlists ==="
source venv/bin/activate
python main.py
python epg_generator.py

echo ""
echo "=== Copying to Raspberry Pi (192.168.1.142) ==="
scp output/master.m3u a-steve@192.168.1.142:~/iptv/
scp output/epg.xml a-steve@192.168.1.142:~/iptv/
echo "✓ Files updated on Pi"

echo ""
echo "Current URLs:"
echo "  M3U: http://192.168.1.142:8090/master.m3u"
echo "  EPG: http://192.168.1.142:8090/epg.xml"
