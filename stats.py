with open("/Users/steve/scripts/djray-iptv/output/master.m3u") as f:
    content = f.read()

lines = content.split("\n")
total_lines = len(lines)
channel_lines = sum(
    1
    for line in lines
    if line.startswith("#EXTINF:-1") and not line.startswith("#EXTINF:-1,---")
)
section_headers = [line for line in lines if line.startswith("#EXTINF:-1,---")]

print(f"Total lines: {total_lines}")
print(f"Channel entries: {channel_lines}")
print(f"Section headers: {len(section_headers)}")
print("\nSections:")
for h in section_headers:
    print(f"  {h}")
