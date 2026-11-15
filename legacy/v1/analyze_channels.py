"""Legacy v1 helper: summarises the archived v1 channel index."""

import json
from collections import Counter
from pathlib import Path

CHANNELS = Path(__file__).resolve().parent / "output" / "channels.json"

with open(CHANNELS, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total unique channels: {len(data)}")

cats = Counter(ch["playlist_source"] for ch in data)
print("\nTop 15 playlists by channel count:")
for name, count in cats.most_common(15):
    print(f"  {name}: {count} channels")

print(f"\nUnique playlist sources: {len(cats)}")