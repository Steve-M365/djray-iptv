#!/bin/bash
# Build final master.m3u with all sections including F1 and AFL

set -e

OUTPUT_DIR="/tmp/opencode/djray-iptv/output"
PLAYLIST_DIR="$OUTPUT_DIR/playlists"
MASTER_M3U="$OUTPUT_DIR/master.m3u"

echo "=========================================="
echo "  Building Master M3U"
echo "=========================================="

# Start the master file
cat > "$MASTER_M3U" << 'EOF'
#EXTM3U
# Apsattv IPTV Hub - Master Playlist
EOF
echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')" >> "$MASTER_M3U"

TOTAL_CHANNELS=0

# Function to add a playlist section
add_section() {
    local title="$1"
    local file="$2"
    local count=0
    
    if [ -f "$file" ]; then
        count=$(grep -c "^#EXTINF:" "$file" 2>/dev/null || echo 0)
        if [ "$count" -gt 0 ]; then
            echo "" >> "$MASTER_M3U"
            echo "# $title ($count channels)" >> "$MASTER_M3U"
            cat "$file" >> "$MASTER_M3U"
            TOTAL_CHANNELS=$((TOTAL_CHANNELS + count))
            echo "  ✓ $title: $count channels"
        fi
    fi
}

# Function to extract channels matching a pattern
extract_channels() {
    local input_file="$1"
    local output_file="$2"
    local pattern="$3"
    
    if [ -f "$input_file" ]; then
        # Extract EXTINF lines and their URLs
        grep -B1 -A1 "$pattern" "$input_file" | grep -E "^#EXTINF:|^https?://" > "$output_file" 2>/dev/null
    fi
}

echo ""
echo "Adding sections..."

# ==================== FORMULA 1 SECTION ====================
echo ""
echo "--- FORMULA 1 ---"

# Extract F1 channels from DaddyLive
F1_TEMP=$(mktemp)
grep -A1 "F1\|Formula" "$PLAYLIST_DIR/daddylive_hd.m3u8" 2>/dev/null | grep -E "^#EXTINF:|^https?://" > "$F1_TEMP" 2>/dev/null

# Extract F1 channels from iptv-org sports
grep -B1 -A1 "F1\|Formula" "$PLAYLIST_DIR/sports_iptvorg.m3u" 2>/dev/null | grep -E "^#EXTINF:|^https?://" >> "$F1_TEMP" 2>/dev/null

# Add F1 section if we have channels
F1_COUNT=$(grep -c "^#EXTINF:" "$F1_TEMP" 2>/dev/null || echo 0)
if [ "$F1_COUNT" -gt 0 ]; then
    echo "" >> "$MASTER_M3U"
    echo "# --- FORMULA 1 ---" >> "$MASTER_M3U"
    echo "# $F1_COUNT F1 channels" >> "$MASTER_M3U"
    cat "$F1_TEMP" >> "$MASTER_M3U"
    TOTAL_CHANNELS=$((TOTAL_CHANNELS + F1_COUNT))
    echo "  ✓ Formula 1: $F1_COUNT channels"
fi
rm -f "$F1_TEMP"

# ==================== AFL SECTION ====================
echo ""
echo "--- AFL ---"

# Extract AFL-related channels from iptv-org AU
AFL_TEMP=$(mktemp)
grep -B1 -A1 -i "afl\|fox footy\|channel 7\|7mate\|7flix\|channel 9\|9now\|channel 10\|10 bold\|10 peach" "$PLAYLIST_DIR/au_iptvorg.m3u" 2>/dev/null | grep -E "^#EXTINF:|^https?://" > "$AFL_TEMP" 2>/dev/null

# Add AFL section
AFL_COUNT=$(grep -c "^#EXTINF:" "$AFL_TEMP" 2>/dev/null || echo 0)
if [ "$AFL_COUNT" -gt 0 ]; then
    echo "" >> "$MASTER_M3U"
    echo "# --- AFL / AUSTRALIAN FOOTY ---" >> "$MASTER_M3U"
    echo "# $AFL_COUNT AFL-related channels" >> "$MASTER_M3U"
    cat "$AFL_TEMP" >> "$MASTER_M3U"
    TOTAL_CHANNELS=$((TOTAL_CHANNELS + AFL_COUNT))
    echo "  ✓ AFL / Australian Footy: $AFL_COUNT channels"
fi
rm -f "$AFL_TEMP"

# ==================== DADDYLIVE SECTION ====================
echo ""
echo "--- DADDYLIVE ---"
add_section "DaddyLive 24/7 Channels" "$PLAYLIST_DIR/daddylive_hd.m3u8"

# ==================== SPORTS SECTION ====================
echo ""
echo "--- SPORTS ---"
add_section "Sports (iptv-org)" "$PLAYLIST_DIR/sports_iptvorg.m3u"

# ==================== AUSTRALIAN TV ====================
echo ""
echo "--- AUSTRALIAN TV ---"
add_section "Australian TV (iptv-org)" "$PLAYLIST_DIR/au_iptvorg.m3u"
add_section "Australian TV (Vortexo)" "$PLAYLIST_DIR/vortexo_au.m3u8"

# ==================== APSATTV PLAYLISTS ====================
echo ""
echo "--- APSATTV PLAYLISTS ---"

# Add each apsattv playlist
for playlist in "$PLAYLIST_DIR"/*.m3u; do
    filename=$(basename "$playlist" .m3u)
    
    # Skip special playlists we already added
    case "$filename" in
        daddylive*|sports_iptvorg|au_iptvorg|vortexo_*) continue ;;
    esac
    
    if [ -f "$playlist" ]; then
        channels=$(grep -c "^#EXTINF:" "$playlist" 2>/dev/null || echo 0)
        if [ "$channels" -gt 0 ]; then
            echo "" >> "$MASTER_M3U"
            echo "# $filename ($channels channels)" >> "$MASTER_M3U"
            cat "$playlist" >> "$MASTER_M3U"
            TOTAL_CHANNELS=$((TOTAL_CHANNELS + channels))
        fi
    fi
done

# Update total count in header
sed -i "1a# Total channels: $TOTAL_CHANNELS" "$MASTER_M3U"

echo ""
echo "=========================================="
echo "  Complete!"
echo "  Total channels: $TOTAL_CHANNELS"
echo "  Master M3U: $MASTER_M3U"
echo "=========================================="
