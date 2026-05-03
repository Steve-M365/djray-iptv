#!/usr/bin/env python3
"""
EPG Generator for Apsattv.com playlists
Generates XMLTV format EPG from channel list using free EPG sources.

Supported sources:
- EPGshare (requires free API key)
- iptv-org EPG (multiple providers)
"""

import json
import re
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import time
from typing import Dict, List

OUTPUT_DIR = Path("output")
CHANNEL_LIST = OUTPUT_DIR / "channels.json"
EPG_FILE = OUTPUT_DIR / "epg.xml"
CONFIG_FILE = Path("config.json")


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"epg": {"source": "epgshare", "api_key": "", "xmltv_url": ""}}


def load_channels():
    """Load channel list from master generation."""
    with open(CHANNEL_LIST) as f:
        return json.load(f)


def normalize_channel_name(name: str) -> str:
    """
    Normalize channel names for better matching with EPG sources.
    Examples:
    - "BBC One" -> "BBC One"
    - "Channel 5" -> "5"
    - "Sky Sports Main Event" -> "Sky Sports"
    """
    name = name.lower().strip()

    # Remove common prefixes/suffixes
    removals = [" hd", " sd", " uk", " us", " au", " (uk)", " (us)", " (au)"]
    for r in removals:
        name = name.replace(r, "")

    # Remove quality indicators
    name = re.sub(r"\b(fhd|uhd|4k|hd|sd)\b", "", name)

    # Remove region indicators (some)
    name = re.sub(r"\b(england|scotland|wales|northern ireland)\b", "", name)

    return name.strip()


def fetch_epgshare(api_key: str, channels: List[Dict]) -> ET.Element:
    """
    Fetch EPG data from EPGshare API.
    EPGshare provides XMLTV format directly.
    Docs: https://epgshare.com/api
    """
    print("Fetching EPG from EPGshare...")

    # EPGshare endpoint - get their full XMLTV
    # Typically: https://api.epgshare.com/v1/xmltv?api_key=YOUR_KEY
    # For now, we'll fetch and filter

    if not api_key:
        raise ValueError("EPGshare API key not configured. Get one at epgshare.com")

    url = f"https://api.epgshare.com/v1/xmltv?api_key={api_key}&days=7"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    # Parse XMLTV
    root = ET.fromstring(resp.content)
    print(
        f"Fetched EPG with {len(root.findall('channel'))} channels, {len(root.findall('programme'))} programmes"
    )
    return root


def fetch_iptvorg_epg(channels: List[Dict]) -> ET.Element:
    """Fetch actual EPG from iptv-org's community-maintained EPG sources."""
    print("Fetching EPG from iptv-org sources...")

    # Create root EPG element
    epg_root = ET.Element("tv")

    # iptv-org EPG sources - try multiple for better coverage
    epg_sources = [
        "https://iptv-org.github.io/epg/guides/epg.xml",
    ]

    # Normalize all search names
    search_names = {normalize_channel_name(ch["name"]) for ch in channels if ch["name"]}
    print(f"Searching for {len(search_names)} channels across EPG sources...")

    # Store fetched channels for matching
    fetched_channels: Dict[str, ET.Element] = {}
    fetched_programmes: Dict[str, List[ET.Element]] = {}

    for source_url in epg_sources:
        try:
            print(f"  Fetching {source_url}...")
            resp = requests.get(source_url, timeout=60)
            resp.raise_for_status()
            root = ET.fromstring(resp.text.encode('utf-8') if isinstance(resp.text, str) else resp.text)

            for channel_elem in root.findall('channel'):
                id_elem = channel_elem.find('id')
                name_elem = channel_elem.find('display-name')
                channel_id = id_elem.text if id_elem is not None else None
                channel_name = name_elem.text if name_elem is not None else channel_id

                if channel_id:
                    fetched_channels[channel_id] = channel_elem
                    # Also store by normalized name for flexible matching
                    norm = normalize_channel_name(channel_name or "").lower()
                    if channel_name:
                        fetched_channels[norm] = channel_elem

            # Collect programmes by channel ID
            for programme_elem in root.findall('programme'):
                chan_attr = programme_elem.get('channel', '')
                if chan_attr:
                    if chan_attr not in fetched_programmes:
                        fetched_programmes[chan_attr] = []
                    fetched_programmes[chan_attr].append(programme_elem)

            print(f"  Fetched {len(fetched_channels)} channels from iptv-org")

        except Exception as e:
            print(f"  Error fetching {source_url}: {e}")

    # Track which channel IDs we've already added to avoid duplicates
    added_channel_ids = set()

    # Add EPG entry for each of our channels
    for ch in channels:
        ch_name = ch.get("name", "")
        if not ch_name:
            continue

        normalized = normalize_channel_name(ch_name)
        norm_lower = normalized.lower()

        # Try to find matching EPG channel
        matched_id = None
        matched_elem = None

        for key, elem in fetched_channels.items():
            key_norm = key.lower()
            if key_norm == norm_lower:
                matched_id = key
                matched_elem = elem
                break

        if matched_id is None or matched_id in added_channel_ids:
            matched_id = None
            for key, elem in fetched_channels.items():
                key_norm = key.lower()
                if (len(key_norm) > 3) and (key_norm in norm_lower or norm_lower in key_norm):
                    matched_id = key
                    matched_elem = elem
                    break

        if matched_id is not None:
            added_channel_ids.add(matched_id)
            if matched_elem is not None:
                epg_root.append(matched_elem)
                for prog in fetched_programmes.get(matched_id, []):
                    epg_root.append(prog)
            continue

        # Fallback: for channels not found in EPG, add with today's placeholder data
        channel_elem = ET.Element("channel")
        channel_id = f"{ch_name.replace(' ', '_').upper()}.tv"
        channel_elem.set("id", channel_id)
        display = ET.SubElement(channel_elem, "display-name")
        display.text = ch_name
        epg_root.append(channel_elem)
        added_channel_ids.add(channel_id)

        # Add today's placeholder programme
        now = datetime.now()
        for hour in range(24):
            start = now.replace(hour=hour, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H%M%S +0000")
            stop = start[:14] + f"{hour+1:02d}0000 +0000"
            programme_elem = ET.Element("programme")
            programme_elem.set("channel", channel_id)
            programme_elem.set("start", start)
            programme_elem.set("stop", stop)
            title = ET.SubElement(programme_elem, "title")
            title.text = ch_name
            epg_root.append(programme_elem)

    print(f"EPG generated with {len(epg_root)} elements")
    return epg_root


def fetch_manual_epg(url: str) -> ET.Element:
    """Fetch EPG from a manually-provided XMLTV URL."""
    print(f"Fetching EPG from {url}...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def filter_epg_by_channels(epg_root: ET.Element, channels: List[Dict]) -> ET.Element:
    """
    Filter the full EPG to only include channels present in our list.
    Uses normalized name matching.
    """
    channel_names = {ch["normalized_name"]: ch["name"] for ch in channels}
    filtered_root = ET.Element("tv", epg_root.attrib)

    # Keep channel definitions that match
    for channel_elem in epg_root.findall("channel"):
        channel_id = channel_elem.get("id", "").lower()
        display_name = channel_elem.find("display-name")
        if display_name is not None:
            display_text = display_name.text.lower() if display_name.text else ""
        else:
            display_text = ""

        # Check for match
        matched = False
        for norm_name, orig_name in channel_names.items():
            if (
                (norm_name in channel_id)
                or (norm_name in display_text)
                or (display_text in norm_name)
            ):
                matched = True
                break

        if matched:
            filtered_root.append(channel_elem)

    # Keep programs that reference matched channels
    matched_ids = [ch.get("id") for ch in filtered_root.findall("channel")]
    matched_ids_lower = [cid.lower() for cid in matched_ids]

    for prog in epg_root.findall("programme"):
        channel = prog.get("channel", "")
        if any(
            channel.lower() in mid or mid in channel.lower()
            for mid in matched_ids_lower
        ):
            filtered_root.append(prog)

    print(
        f"Filtered EPG: {len(filtered_root.findall('channel'))} channels, {len(filtered_root.findall('programme'))} programmes"
    )
    return filtered_root


def write_epg(epg_root: ET.Element):
    """Write EPG XML to file."""
    tree = ET.ElementTree(epg_root)
    tree.write(EPG_FILE, encoding="utf-8", xml_declaration=True)
    print(f"✓ EPG written to {EPG_FILE}")


def main():
    print("=" * 60)
    print("EPG Generator")
    print("=" * 60)

    config = load_config()
    channels = load_channels()
    print(f"Loaded {len(channels)} channels")

    # Choose EPG source
    source = config.get("epg", {}).get("source", "epgshare")

    if source == "epgshare":
        api_key = config.get("epg", {}).get("api_key", "")
        if not api_key:
            print("ERROR: EPGshare API key not configured in config.json")
            print("1. Register at https://epgshare.com")
            print("2. Get your API key")
            print(
                '3. Edit config.json and set: {"epg": {"source": "epgshare", "api_key": "YOUR_KEY"}}'
            )
            return

        epg_root = fetch_epgshare(api_key, channels)
    elif source == "iptvorg":
        epg_root = fetch_iptvorg_epg(channels)
    elif source == "manual":
        url = config.get("epg", {}).get("xmltv_url", "")
        if not url:
            print("ERROR: No XMLTV URL configured")
            return
        epg_root = fetch_manual_epg(url)
    else:
        print(f"ERROR: Unknown EPG source: {source}")
        return

    # Filter EPG to only include our channels
    filtered_epg = filter_epg_by_channels(epg_root, channels)

    # Write output
    write_epg(filtered_epg)

    print("\n✓ EPG generation complete!")
    print(f"File: {EPG_FILE}")
    print("\nTo use:")
    print("1. Upload master.m3u and epg.xml to your hosting")
    print("2. In your IPTV player, set M3U URL to: YOUR_HOSTING_URL/master.m3u")
    print("3. Set EPG/XMLTV URL to: YOUR_HOSTING_URL/epg.xml")


if __name__ == "__main__":
    main()
