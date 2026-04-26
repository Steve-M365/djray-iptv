#!/usr/bin/env python3
"""
Apsattv.com Playlist Aggregator
Fetches all M3U playlists from apsattv.com/streams.html and creates:
1. master.m3u - single playlist with categorized section headers
2. epg.xml - XMLTV formatted EPG (using EPGshare or other free sources)

Usage:
    python main.py [--config config.json]
"""

import json
import requests
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# Configuration
APSV_URL = "https://www.apsattv.com/streams.html"
PLAYLIST_BASE = "https://www.apsattv.com/"
OUTPUT_DIR = Path("output")
MASTER_M3U = OUTPUT_DIR / "master.m3u"
CHANNEL_LIST = OUTPUT_DIR / "channels.json"
CONFIG_FILE = Path("config.json")

# Category definitions based on URL patterns and naming
CATEGORIES = {
    "Main Playlists": [
        "lg.m3u",
        "distro.m3u",
        "metax.m3u",
        "whaletvplus_all.m3u",
        "whaletvplus_us.m3u",
    ],
    "LG Regional": lambda url: (
        url.endswith("lg.m3u")
        and not url.endswith("whaletvplus_all.m3u")
        and not url.endswith("whaletvplus_us.m3u")
    ),
    "Samsung Regional": lambda url: (
        url.split("/")[-1].startswith("ssung") and url.endswith(".m3u")
    ),
    "Australian": ["10fast.m3u", "9fast.m3u", "kogantvplus.m3u"],
    "Brazilian": ["moviearkbr.m3u", "redeitv.m3u", "soultv.m3u", "tclbr.m3u"],
    "Platform/Device": [
        "firetv.m3u",
        "xiaomi.m3u",
        "vizio.m3u",
        "tcl.m3u",
        "tclplus.m3u",
        "rok.m3u",
        "xumo.m3u",
        "zeasn.m3u",
    ],
    "Content/Services": [
        "freelivesports.m3u",
        "freemoviesplus.m3u",
        "freetv.m3u",
        "sportstv.m3u",
        "klowd.m3u",
        "rewardedtv.m3u",
        "hp.m3u",
    ],
    "Specialized": [
        "vidaa.m3u",
        "igocast.m3u",
        "localnow.m3u",
        "tablo.m3u",
        "galxytv.m3u",
        "rakuten-jp.m3u",
        "tubi_all.m3u",
        "roku_all.m3u",
    ],
}

EXTERNAL_PLAYLISTS = {
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/refs/heads/main/playlists/tubi_all.m3u": "External: Tubi TV",
    "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/refs/heads/main/playlists/roku_all.m3u": "External: Roku Channel",
}


def load_config():
    """Load configuration file or create default."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    else:
        config = {
            "epg": {
                "source": "epgshare",  # Options: epgshare, iptvorg, manual
                "api_key": "",  # For EPGshare
                "xmltv_url": "",  # For direct XMLTV URL
            },
            "channels": {
                "exclude_patterns": [],  # Regex patterns to exclude channels
                "name_cleanup": {},  # Map of channel name corrections
            },
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return config


def fetch_page(url: str) -> str:
    """Fetch HTML page from URL."""
    print(f"Fetching {url}...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def extract_playlist_urls(html: str) -> List[Tuple[str, str]]:
    """
    Extract all .m3u URLs from the page with their display names.
    Returns list of (url, name) tuples.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls = []

    # Find all text that looks like .m3u URLs
    text = soup.get_text()

    # Pattern for URLs
    patterns = [r'https?://[^\s"\']+\.m3u', r'https?://[^\s<>"]+\.m3u']

    found_urls = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            url = match.group(0).rstrip(".,;:)")
            if url not in found_urls:
                # Try to get a human name from nearby text
                name = extract_name_from_context(text, match.start())
                urls.append((url, name))
                found_urls.add(url)

    # Also include external playlists
    for url, name in EXTERNAL_PLAYLISTS.items():
        if url not in found_urls:
            urls.append((url, name))
            found_urls.add(url)

    print(f"Found {len(urls)} unique playlists")
    return urls


def extract_name_from_context(text: str, position: int) -> str:
    """Extract a reasonable name for a playlist from nearby text."""
    # Look backwards for a line that might be the title
    start = max(0, position - 200)
    snippet = text[start:position]

    # Clean up
    lines = [l.strip() for l in snippet.split("\n") if l.strip()]
    for line in reversed(lines):
        # Remove common punctuation
        line = line.rstrip(".:;,-")
        if 3 < len(line) < 50 and not line.startswith("http"):
            return line

    return "Unknown Playlist"


def categorize_playlist(url: str, name: str) -> str:
    """Determine which category a playlist belongs to."""
    filename = url.split("/")[-1]

    for category, criterion in CATEGORIES.items():
        if callable(criterion):
            if criterion(url):
                return category
        elif isinstance(criterion, list):
            if filename in criterion:
                return category
        elif isinstance(criterion, str):
            if filename == criterion:
                return category

    # Check external
    if url in EXTERNAL_PLAYLISTS:
        return "External/Third-Party"

    return "Other/Misc"


def fetch_m3u_content_with_retry(
    url: str, max_retries: int = 3, backoff_factor: float = 1.0
) -> List[str]:
    """Fetch and parse M3U file with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"  Fetching {url} (attempt {attempt + 1}/{max_retries})...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            lines = resp.text.splitlines()
            return [line.strip() for line in lines if line.strip()]
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                time.sleep(sleep_time)
                continue
            print(f"    Timeout fetching {url} after {max_retries} attempts")
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                time.sleep(sleep_time)
                continue
            print(f"    Error fetching {url}: {e}")
            return []
    return []


def parse_m3u_channels(lines: List[str]) -> List[Dict]:
    """
    Parse M3U format lines and extract channel entries.
    M3U format: #EXTINF followed by URL
    Returns list of dicts with 'name' and 'url' and 'raw' (full entry).
    """
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF:"):
            # Extract info
            info = line[8:]  # Remove #EXTINF:
            # Typically format: duration, attributes, channel name
            # Example: #EXTINF:-1 tvg-id="" tvg-logo="",Channel Name
            parts = info.split(",", 1)
            if len(parts) == 2:
                duration = parts[0].strip()
                name = parts[1].strip()
            else:
                name = parts[0].strip()

            # Next line should be URL
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                url = lines[i + 1].strip()
                channels.append(
                    {"name": name, "url": url, "raw_inf": line, "raw_url": url}
                )
                i += 2
                continue
        i += 1

    return channels


def generate_master_m3u(
    categorized_playlists: Dict[str, List[Tuple[str, str, List[Dict]]]],
):
    """Generate the master.m3u file with section headers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(MASTER_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Apsattv.com aggregated playlist\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"# Total playlists: {sum(len(v) for v in categorized_playlists.values())}\n\n"
        )

        for category in sorted(CATEGORIES.keys()) + [
            "External/Third-Party",
            "Other/Misc",
        ]:
            if category not in categorized_playlists:
                continue

            playlists = categorized_playlists[category]
            if not playlists:
                continue

            f.write(f"#EXTINF:-1,--- {category} ---\n\n")

            for url, name, channels in playlists:
                f.write(f"# Playlist: {name}\n")
                f.write(f"# Source: {url}\n")
                f.write(f"# Channels: {len(channels)}\n\n")
                for ch in channels:
                    f.write(f"{ch['raw_inf']}\n")
                    f.write(f"{ch['raw_url']}\n")
                    f.write("\n")
                f.write("\n")

    print(f"✓ Master M3U written to {MASTER_M3U}")


def save_channel_index(all_channels: List[Dict]):
    """Save a JSON index of all channels for EPG processing."""
    channels_data = []
    seen = set()
    for ch in all_channels:
        # Normalize name for matching
        norm_name = ch["name"].lower().strip()
        if norm_name not in seen:
            channels_data.append(
                {
                    "name": ch["name"],
                    "normalized_name": norm_name,
                    "url": ch["url"],
                    "playlist_source": ch.get("playlist_source", "unknown"),
                }
            )
            seen.add(norm_name)

    with open(CHANNEL_LIST, "w", encoding="utf-8") as f:
        json.dump(channels_data, f, indent=2)

    print(
        f"✓ Channel index written to {CHANNEL_LIST} ({len(channels_data)} unique channels)"
    )


def process_single_playlist(url: str, name: str) -> Tuple[str, str, str, List[Dict]]:
    """Process a single playlist: categorize, fetch, parse. Returns (category, url, name, channels)."""
    category = categorize_playlist(url, name)
    channels = fetch_m3u_content_with_retry(url)
    parsed_channels = parse_m3u_channels(channels)

    # Add source info to each channel
    for ch in parsed_channels:
        ch["playlist_source"] = name or url

    return (category, url, name or url.split("/")[-1], parsed_channels)


def main():
    """Main execution."""
    print("=" * 60)
    print("Apsattv.com Playlist Aggregator")
    print("=" * 60)

    config = load_config()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch apsattv page and get playlist URLs
    html = fetch_page(APSV_URL)
    urls_with_names = extract_playlist_urls(html)

    print(f"\nFound {len(urls_with_names)} playlists")
    print("Fetching playlists concurrently...")

    # 2. Categorize and fetch each playlist concurrently
    categorized = {
        cat: []
        for cat in list(CATEGORIES.keys()) + ["External/Third-Party", "Other/Misc"]
    }

    all_channels = []
    completed = 0

    # Use ThreadPoolExecutor to fetch playlists concurrently
    with ThreadPoolExecutor(max_workers=15) as executor:
        # Submit all tasks
        future_to_playlist = {
            executor.submit(process_single_playlist, url, name): (url, name)
            for url, name in urls_with_names
        }

        # Process completed tasks
        for future in as_completed(future_to_playlist):
            try:
                category, url, display_name, parsed_channels = future.result()
                categorized[category].append((url, display_name, parsed_channels))
                all_channels.extend(parsed_channels)
                completed += 1
                print(
                    f"  Progress: {completed}/{len(urls_with_names)} | "
                    f"Category: {category} | Channels: {len(parsed_channels)}"
                )
            except Exception as e:
                url, name = future_to_playlist[future]
                print(f"  Error processing {url}: {e}")

    # 3. Generate master.m3u
    generate_master_m3u(categorized)

    # 4. Save channel index
    save_channel_index(all_channels)

    print("\n" + "=" * 60)
    print("Generation complete!")
    print(f"Master M3U: {MASTER_M3U}")
    print(f"Channel Index: {CHANNEL_LIST}")
    print("\nNext steps:")
    print("1. Configure EPG source in config.json")
    print("2. Run: python epg_generator.py")
    print("3. Deploy files to hosting (see README.md)")
    print("=" * 60)


if __name__ == "__main__":
    main()
