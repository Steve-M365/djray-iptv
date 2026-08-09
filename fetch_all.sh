#!/bin/bash
# Fetch all playlists from apsattv.com and merge into master.m3u

set -e

OUTPUT_DIR="/tmp/opencode/djray-iptv/output"
PLAYLIST_DIR="$OUTPUT_DIR/playlists"
MASTER_M3U="$OUTPUT_DIR/master.m3u"
URLS_FILE="$OUTPUT_DIR/playlist_urls.txt"

mkdir -p "$PLAYLIST_DIR"

echo "=========================================="
echo "  Apsattv Playlist Fetcher"
echo "=========================================="

# Read URLs
if [ ! -f "$URLS_FILE" ]; then
    echo "Fetching playlist URLs from apsattv.com..."
    curl -sL "https://www.apsattv.com/streams.html" | grep -oE 'https?://[^<>"]+\.m3u' | sort -u > "$URLS_FILE"
fi

TOTAL=$(wc -l < "$URLS_FILE")
echo "Found $TOTAL playlists"
echo ""

# Download each playlist
COUNT=0
FAILED=0

while IFS= read -r url; do
    COUNT=$((COUNT + 1))
    filename=$(basename "$url" .m3u)
    
    # Download with timeout
    if curl -sL --connect-timeout 10 --max-time 30 "$url" -o "$PLAYLIST_DIR/$filename.m3u" 2>/dev/null; then
        # Check if file has content
        if [ -s "$PLAYLIST_DIR/$filename.m3u" ]; then
            channels=$(grep -c "^#EXTINF:" "$PLAYLIST_DIR/$filename.m3u" 2>/dev/null || echo 0)
            printf "[%d/%d] %-30s %s channels\n" "$COUNT" "$TOTAL" "$filename" "$channels"
        else
            printf "[%d/%d] %-30s EMPTY\n" "$COUNT" "$TOTAL" "$filename"
            rm -f "$PLAYLIST_DIR/$filename.m3u"
            FAILED=$((FAILED + 1))
        fi
    else
        printf "[%d/%d] %-30s FAILED\n" "$COUNT" "$TOTAL" "$filename"
        FAILED=$((FAILED + 1))
    fi
done < "$URLS_FILE"

echo ""
echo "Downloaded: $((TOTAL - FAILED))/$TOTAL"
echo "Failed: $FAILED"

# Build master M3U
echo ""
echo "Building master.m3u..."

cat > "$MASTER_M3U" << 'EOF'
#EXTM3U
# Apsattv.com aggregated playlist
EOF
echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> "$MASTER_M3U"
echo "# Playlists: $((TOTAL - FAILED))" >> "$MASTER_M3U"

# Count total channels
TOTAL_CHANNELS=0

# Add playlists by category
for playlist in "$PLAYLIST_DIR"/*.m3u; do
    if [ -f "$playlist" ]; then
        name=$(basename "$playlist" .m3u)
        channels=$(grep -c "^#EXTINF:" "$playlist" 2>/dev/null || echo 0)
        TOTAL_CHANNELS=$((TOTAL_CHANNELS + channels))
        
        echo "" >> "$MASTER_M3U"
        echo "# $name ($channels channels)" >> "$MASTER_M3U"
        cat "$playlist" >> "$MASTER_M3U"
    fi
done

echo "# Total channels: $TOTAL_CHANNELS" >> "$MASTER_M3U"

echo ""
echo "=========================================="
echo "  Complete!"
echo "  Master M3U: $MASTER_M3U"
echo "  Total channels: $TOTAL_CHANNELS"
echo "=========================================="
