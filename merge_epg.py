#!/usr/bin/env python3
"""Merge multiple EPG XML files into one combined EPG."""

import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import sys

OUTPUT_DIR = Path("/tmp/opencode/djray-iptv/output")
MERGED_FILE = OUTPUT_DIR / "epg.xml"

# EPG sources in priority order (first match wins)
EPG_SOURCES = [
    OUTPUT_DIR / "vortexo_au_epg.xml",      # 5676 channels - best AU coverage
    OUTPUT_DIR / "mjh_all_epg.xml",          # 295 channels - worldwide
    OUTPUT_DIR / "mjh_sydney_epg.xml",       # 179 channels - AU Sydney
    OUTPUT_DIR / "mjh_world_epg.xml",        # 4 channels - world
]


def parse_epg(filepath):
    """Parse an EPG XML file and return channels and programmes."""
    channels = {}
    programmes = []
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        for channel in root.findall('channel'):
            ch_id = channel.get('id')
            if ch_id:
                channels[ch_id] = channel
        
        for prog in root.findall('programme'):
            ch = prog.get('channel')
            if ch:
                programmes.append(prog)
        
        print(f"  Parsed {filepath.name}: {len(channels)} channels, {len(programmes)} programmes")
    except Exception as e:
        print(f"  Error parsing {filepath.name}: {e}")
    
    return channels, programmes


def merge_epg():
    """Merge all EPG sources into one file."""
    print("Merging EPG sources...")
    print("=" * 50)
    
    all_channels = {}
    all_programmes = []
    seen_programmes = set()
    
    for source in EPG_SOURCES:
        if not source.exists():
            print(f"  Skipping {source.name} (not found)")
            continue
        
        channels, programmes = parse_epg(source)
        
        # Add channels (skip duplicates)
        for ch_id, channel in channels.items():
            if ch_id not in all_channels:
                all_channels[ch_id] = channel
        
        # Add programmes (skip duplicates by channel+start time)
        for prog in programmes:
            key = (prog.get('channel'), prog.get('start'))
            if key not in seen_programmes:
                all_programmes.append(prog)
                seen_programmes.add(key)
    
    print("=" * 50)
    print(f"Total unique channels: {len(all_channels)}")
    print(f"Total unique programmes: {len(all_programmes)}")
    
    # Build merged XML
    root = ET.Element("tv")
    root.set("generator-info-name", "DJRay IPTV Hub")
    root.set("source-info-name", "Multiple sources merged")
    
    # Add channels
    for ch_id in sorted(all_channels.keys()):
        root.append(all_channels[ch_id])
    
    # Add programmes
    for prog in all_programmes:
        root.append(prog)
    
    # Write output
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(MERGED_FILE, encoding="utf-8", xml_declaration=True)
    
    print(f"\nMerged EPG written to: {MERGED_FILE}")
    print(f"File size: {MERGED_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Also create a compressed version
    import gzip
    gz_file = OUTPUT_DIR / "epg.xml.gz"
    with open(MERGED_FILE, 'rb') as f_in:
        with gzip.open(gz_file, 'wb') as f_out:
            f_out.write(f_in.read())
    
    print(f"Compressed EPG written to: {gz_file}")
    print(f"Compressed size: {gz_file.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    merge_epg()
