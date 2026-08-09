#!/usr/bin/env python3
"""
Build AFL playlist dynamically from EPG data.
Finds channels with AFL programmes in the EPG, matches them to M3U streams.
Run: python3 build_afl.py
"""
import gzip, re

EPG_FILE = "output/epg.xml.gz"
M3U_FILE = "output/master.m3u"
OUTPUT = "output/sources/afl.m3u"
# Strict keywords - must be whole words
AFL_KEYWORDS_RE = re.compile(r'\b(?:afl|australian football|footy|7afl|fox footy)\b', re.IGNORECASE)
EXCLUDE_RE = re.compile(r'aflam|aflak', re.IGNORECASE)

def load_epg_afl_ids():
    with gzip.open(EPG_FILE, "rt") as f:
        epg = f.read()
    progs = re.findall(
        r'<programme[^>]*channel="([^"]+)"[^>]*>.*?<title[^>]*>([^<]+)</title>',
        epg, re.DOTALL
    )
    ids = set()
    for ch, title in progs:
        if AFL_KEYWORDS_RE.search(title) and not EXCLUDE_RE.search(title):
            ids.add(ch)
    return ids

def load_m3u():
    with open(M3U_FILE, "r") as f:
        content = f.read()
    channels = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#EXTINF:"):
            tvg_id = ""
            m = re.search(r'tvg-id="([^"]*)"', ln)
            if m:
                tvg_id = m.group(1)
            name_m = re.search(r',(.+)$', ln)
            name = name_m.group(1).strip() if name_m else ""
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith("#"):
                    channels.append({"extinf": ln, "url": url, "tvg_id": tvg_id, "name": name})
                    i += 2
                    continue
        i += 1
    return channels

def is_afl_name(name):
    if EXCLUDE_RE.search(name):
        return False
    return bool(AFL_KEYWORDS_RE.search(name))

def main():
    print("Scanning EPG for AFL programmes...")
    afl_ids = load_epg_afl_ids()
    print(f"  Found {len(afl_ids)} EPG channels with AFL content")

    print("Loading master M3U...")
    channels = load_m3u()
    print(f"  Loaded {len(channels)} channels")

    # Match by EPG ID
    matched = [ch for ch in channels if ch["tvg_id"] in afl_ids]

    # Also add any channel with AFL/7AFL in the name (strict)
    for ch in channels:
        if ch not in matched and is_afl_name(ch["name"]):
            matched.append(ch)

    # Deduplicate by URL
    seen = set()
    unique = []
    for ch in matched:
        if ch["url"] not in seen:
            seen.add(ch["url"])
            unique.append(ch)

    print(f"  Matched {len(unique)} unique AFL channels")

    with open(OUTPUT, "w") as f:
        f.write("#EXTM3U\n")
        for ch in unique:
            f.write(ch["extinf"] + "\n")
            f.write(ch["url"] + "\n")

    print(f"Wrote {OUTPUT} with {len(unique)} channels")
    for ch in unique:
        print(f"  - {ch['name']}")

if __name__ == "__main__":
    main()
