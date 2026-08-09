#!/bin/bash
# Quick setup script for djray-iptv

echo "=== Apsattv IPTV Setup ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create output directory
mkdir -p output

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.json if you want EPGshare (or use default iptvorg)"
echo "2. Run: python main.py"
echo "3. Run: python epg_generator.py"
echo "4. Deploy output/ to GitHub Pages"
echo ""
