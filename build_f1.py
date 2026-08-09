#!/usr/bin/env python3
"""
Build Formula 1 playlist from master M3U.
Matches channel names containing F1/Formula 1 keywords.
Run: python3 build_f1.py
"""
import re

M3U_FILE = "output/master.m3u"
OUTPUT = "output/sources/formula1.m3u"
F1_NAME_RE = re.compile(r'\b(?:f1|formula\s*1|formula\s*one)\b', re.IGNORECASE)

def load_m3u():
    with open(M3U_FILE, "r") as f:
        content = f.read()
    channels = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#EXTINF:"):
            name_m = re.search(r',(.+)$', ln)
            name = name_m.group(1).strip() if name_m else ""
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith("#"):
                    channels.append({"extinf": ln, "url": url, "name": name})
                    i += 2
                    continue
        i += 1
    return channels

def main():
    channels = load_m3u()
    matched = [ch for ch in channels if F1_NAME_RE.search(ch["name"])]

    seen = set()
    unique = []
    for ch in matched:
        if ch["url"] not in seen:
            seen.add(ch["url"])
            unique.append(ch)

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
