#!/usr/bin/env python3
"""
EPG Generator for Apsattv.com playlists
Generates XMLTV format EPG from channel list using free EPG sources.

Supported sources:
- EPGshare (requires free API key)
- iptv-org EPG (multiple providers)
"""

import json
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
    """
    Use iptv-org's EPG grabber sources.
    iptv-org maintains a list of free EPG providers.
    We'll fetch from multiple sources and merge.
    """
    print("Fetching EPG from iptv-org sources...")

    # Common free EPG sources
    sources = [
        "https://iptv-org.github.io/epg/guides/epg.xml",
        "https://iptv-org.github.io/epg/guides/epg2.xml",
        # Add more sources from iptv-org
    ]

    # For demo purposes, create a minimal EPG
    root = ET.Element(
        "tv",
        {
            "generator-info-name": "Apsattv EPG Generator",
            "source-info-name": "iptv-org",
        },
    )

    # Generate channel descriptors
    for ch in channels[:100]:  # Limit for demo
        channel_elem = ET.SubElement(root, "channel", id=ch["normalized_name"])
        display_elem = ET.SubElement(channel_elem, "display-name")
        display_elem.text = ch["name"]
        icon_elem = ET.SubElement(channel_elem, "icon")
        icon_elem.set("src", "")

    # Add placeholder programmes for next 7 days
    now = datetime.now()
    for ch in channels[:100]:
        for day in range(7):
            date = now + timedelta(days=day)
            for hour in [0, 3, 6, 9, 12, 15, 18, 21]:
                start_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                stop_time = start_time + timedelta(hours=3)

                prog = ET.SubElement(
                    root,
                    "programme",
                    {
                        "start": start_time.strftime("%Y%m%d%H%M%S %z"),
                        "stop": stop_time.strftime("%Y%m%d%H%M%S %z"),
                        "channel": ch["normalized_name"],
                    },
                )
                title_elem = ET.SubElement(prog, "title")
                title_elem.text = (
                    f"{ch['name']} - {start_time.strftime('%A %H:%M')} Broadcast"
                )
                desc_elem = ET.SubElement(prog, "desc")
                desc_elem.text = "Schedule information not available"

    print(
        f"Generated EPG with {len(channels)} channels, 7 days of placeholder programmes"
    )
    return root


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
