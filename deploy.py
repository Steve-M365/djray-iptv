#!/usr/bin/env python3
"""
Quick deployment script for GitHub Pages.
Creates a repo and pushes files automatically (requires GitHub CLI 'gh').
"""

import subprocess
import sys
from pathlib import Path


def run_cmd(cmd, check=True):
    """Run shell command."""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print("GitHub Pages Deployment Script")
    print("=" * 60)

    output_dir = Path("output")
    if not output_dir.exists():
        print(
            "ERROR: output/ directory not found. Run main.py and epg_generator.py first."
        )
        sys.exit(1)

    # Check if gh CLI is installed
    result = run_cmd("gh --version", check=False)
    if result.returncode != 0:
        print("ERROR: GitHub CLI (gh) is not installed.")
        print("Install from: https://cli.github.com/")
        print("Or manually follow these steps:")
        print("  1. Create a new public repo on github.com")
        print("  2. git init && git add . && git commit -m 'Initial'")
        print("  3. git remote add origin <repo-url>")
        print("  4. git push -u origin main")
        print("  5. Enable Pages in repo Settings → Pages")
        sys.exit(1)

    # Get repo name
    repo_name = input("Enter GitHub repository name (e.g., apsattv-m3u): ").strip()
    if not repo_name:
        repo_name = "apsattv-m3u"

    # Get GitHub username
    username = input("Enter your GitHub username: ").strip()
    if not username:
        print("ERROR: Username required")
        sys.exit(1)

    # Initialize git if not already
    if not Path(".git").exists():
        run_cmd("git init")
        run_cmd("git add .")
        run_cmd("git commit -m 'Initial commit'")
    else:
        run_cmd("git add output/")
        run_cmd("git commit -m 'Update playlists and EPG'")

    # Add remote
    remote_url = f"git@github.com:{username}/{repo_name}.git"
    run_cmd(f"git remote add origin {remote_url} || true")

    # Push
    print(f"\nPushing to {remote_url}...")
    run_cmd("git push -u origin main --force")

    print("\n" + "=" * 60)
    print("✓ Deployment complete!")
    print(f"Your files are now at:")
    print(f"  M3U: https://{username}.github.io/{repo_name}/master.m3u")
    print(f"  EPG: https://{username}.github.io/{repo_name}/epg.xml")
    print("\nTo activate GitHub Pages:")
    print("1. Go to https://github.com/{username}/{repo_name}/settings/pages")
    print("2. Under 'Build and deployment', select 'Deploy from a branch'")
    print("3. Source: Branch: main, Folder: / (root)")
    print("4. Click Save")
    print("5. Wait 1-5 minutes for site to go live")
    print("=" * 60)


if __name__ == "__main__":
    main()
