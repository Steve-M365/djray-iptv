import json
from pathlib import Path
from collections import Counter

with open((Path(__file__).parent / "output" / "channels.json")) as f:
    data = json.load(f)

print(f"Total unique channels: {len(data)}")

# Count by playlist source
cats = Counter(ch["playlist_source"] for ch in data)
print(f"\nTop 15 playlists by channel count:")
for name, count in cats.most_common(15):
    print(f"  {name}: {count} channels")

# Check which categories are represented
print(f"\nUnique playlist sources: {len(cats)}")
