#!/bin/bash
# Quick Deploy Script for Apsattv IPTV Aggregator
# This script automates the full deployment to GitHub Pages

set -e

echo "============================================"
echo "  Apsattv IPTV — Deploy to GitHub Pages"
echo "============================================"
echo ""

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required but not found"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git required but not found"; exit 1; }

# Step 1: Setup environment
echo "Step 1: Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Step 2: Generate master M3U
echo "Step 2: Generating master playlist..."
python main.py

# Step 3: Generate EPG
echo "Step 3: Generating EPG..."
python epg_generator.py

# Step 4: Git setup
echo "Step 4: Preparing for deployment..."

read -p "Enter your GitHub username: " username
if [ -z "$username" ]; then
    echo "ERROR: Username required"
    exit 1
fi

repo_name="apsattv-m3u"
read -p "Repository name [$repo_name]: " input_repo
repo_name=${input_repo:-$repo_name}

# Initialize git if needed
if [ ! -d ".git" ]; then
    git init
fi

git add output/
git commit -m "Deploy $(date +%Y-%m-%d)" || echo "No changes to commit"

# Add remote
remote_url="git@github.com:${username}/${repo_name}.git"
git remote remove origin 2>/dev/null || true
git remote add origin "$remote_url"

echo ""
echo "============================================"
echo "  Ready to push!"
echo "============================================"
echo ""
echo "Files will be pushed to: $remote_url"
echo "After pushing, enable GitHub Pages:"
echo "  Settings → Pages → Source: main branch /root"
echo ""
read -p "Push now? (y/n): " push_confirm
if [ "$push_confirm" = "y" ] || [ "$push_confirm" = "Y" ]; then
    git push -u origin main
    echo ""
    echo "✓ Push complete!"
    echo ""
    echo "Your playlist URL:"
    echo "  https://${username}.github.io/${repo_name}/master.m3u"
    echo ""
    echo "Your EPG URL:"
    echo "  https://${username}.github.io/${repo_name}/epg.xml"
    echo ""
    echo "Next: Enable GitHub Pages (see instructions above)."
else
    echo "Skipped push. You can manually push later with: git push -u origin main"
fi

echo ""
echo "Done! 🎉"
