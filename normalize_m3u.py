#!/usr/bin/env python3
"""
DJRay IPTV - M3U Normalizer for TiviMate
Cleans up groups, adds metadata, strips tags, sorts, generates per-category files.
"""

import re
import os
import gzip
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime

OUTPUT_DIR = Path("output")
PLAYLIST_DIR = OUTPUT_DIR / "playlists"

# ==================== GROUP MAPPING ====================
# Maps 300+ messy groups into ~20 clean TiviMate categories
GROUP_MAP = {
    # Sports
    "sports": "Sports",
    "sport": "Sports",
    "Sports": "Sports",
    "SPORTS": "Sports",
    "Sports On Now": "Sports",
    "Live Events": "Sports",
    "FreeLiveSports": "Sports",
    "Football": "Sports",
    "Soccer": "Sports",
    "Baseball": "Sports",
    "Basketball": "Sports",
    "Boxing": "Sports",
    "Golf": "Sports",
    "Tennis": "Sports",
    "Cricket": "Sports",
    "Rugby": "Sports",
    "Hockey": "Sports",
    "Fishing": "Sports",
    "Hunting": "Sports",
    "Outdoor": "Sports",
    "Outdoor;Sports": "Sports",
    "Public;Sports": "Sports",
    "Auto": "Sports",
    "Auto & Motorsports": "Sports",
    "Racing": "Sports",
    "Billiards": "Sports",
    "E Sports": "Sports",
    "General;Sports": "Sports",
    "News;Sports": "Sports",
    "Entertainment;Sports": "Sports",
    "Culture;Sports": "Sports",
    "Kids;Sports": "Sports",
    "Auto;Outdoor;Sports": "Sports",
    "Auto;Outdoor;Series;Sports": "Sports",
    "Comedy;Movies;Series;Sports": "Sports",
    "DLHD 24/7": "Sports",
    "Live Events": "Sports",
    "Olympics": "Sports",

    # Formula 1 / Motorsport
    "RakutenTV🇬🇧: Formula 1": "Formula 1",
    "RakutenTV🇬🇧: Sports": "Sports",

    # News
    "News": "News",
    "NEWS + OPINION": "News",
    "Local News": "News",
    "National News": "News",
    "Global News": "News",
    "Live News": "News",
    "Business News": "News",
    "Environmental News": "News",
    "Political News": "News",
    "Entertainment News": "News",
    "Pop Culture": "News",
    "Informations": "News",
    "Informative": "News",
    "Informative,Featured": "News",
    "Weather": "News",
    "Bus./Financial": "News",
    "Law": "News",

    # Entertainment
    "Entertainment": "Entertainment",
    "ENTERTAINMENT": "Entertainment",
    "TV & Entertainment": "Entertainment",
    "Featured,Entertainment": "Entertainment",
    "Entertainment,Featured": "Entertainment",
    "Entertainment,Kids": "Entertainment",
    "Entertainment;Kids": "Entertainment",
    "Comedy": "Entertainment",
    "COMEDY": "Entertainment",
    "Dark Comedy": "Entertainment",
    "Sitcom": "Entertainment",
    "Reality": "Entertainment",
    "REALITY": "Entertainment",
    "Game Show": "Entertainment",
    "GAME SHOWS": "Entertainment",
    "Games & Competition": "Entertainment",
    "Talk Show": "Entertainment",
    "Variety Show": "Entertainment",
    "Black Entertainment": "Entertainment",
    "LGBTQ,Featured": "Entertainment",
    "Divertissements": "Entertainment",
    "FEATURED": "Entertainment",
    "HOME": "Entertainment",
    "HP TV+": "Entertainment",

    # Movies
    "Movies": "Movies",
    "MOVIES": "Movies",
    "Movie Channels": "Movies",
    "Films": "Movies",
    "TV & Movies": "Movies",
    "Featured,Horror": "Movies",
    "Horror": "Movies",
    "Horror & Crime": "Movies",
    "Horror,Movies,Featured,Special Interest": "Movies",
    "Mystery": "Movies",
    "Sci-Fi & Supernatural": "Movies",
    "Science Fiction": "Movies",
    "Paranormal": "Movies",
    "Western": "Movies",
    "WESTERNS + CLASSICS": "Movies",
    "Crime": "Movies",
    "Crime Drama": "Movies",
    "True Crime": "Movies",
    "Crime et Mystère": "Movies",
    "ACTION + DRAMA": "Movies",
    "Thriller": "Movies",

    # Kids & Family
    "Kids": "Kids & Family",
    "KIDS + FAMILY": "Kids & Family",
    "Kids & Family": "Kids & Family",
    "Kids,Featured,Entertainment": "Kids & Family",
    "Family": "Kids & Family",
    "Faith & Family": "Kids & Family",
    "Animated": "Kids & Family",
    "Animation;Kids": "Kids & Family",
    "Education;Kids": "Kids & Family",
    "Early Education": "Kids & Family",
    "Children-Music": "Kids & Family",
    "Jeunesse": "Kids & Family",
    "Cartoons": "Kids & Family",

    # Music
    "MUSIC": "Music",
    "Music": "Music",
    "Music Talk": "Music",
    "Musique": "Music",
    "Hip-Hop": "Music",
    "Karaoke": "Music",

    # Documentary
    "Documentary": "Documentary",
    "Documentaries": "Documentary",
    "Documentaires": "Documentary",
    "HISTORY + DOCS": "Documentary",
    "History": "Documentary",
    "Science & Nature": "Documentary",
    "Nature": "Documentary",
    "Nature & Travel": "Documentary",
    "NATURE + SCIENCE": "Documentary",
    "Animals": "Documentary",
    "Environment": "Documentary",
    "Science": "Documentary",
    "Art": "Documentary",
    "Biography": "Documentary",
    "Computers": "Documentary",
    "Gaming & Tech": "Documentary",
    "Gaming": "Documentary",

    # Lifestyle
    "Lifestyle": "Lifestyle",
    "Lifestyle / Education": "Lifestyle",
    "Lifestyle;Relax": "Lifestyle",
    "Travel & Lifestyle": "Lifestyle",
    "FOOD + TRAVEL": "Lifestyle",
    "Food": "Lifestyle",
    "Cooking": "Lifestyle",
    "Cuisine": "Lifestyle",
    "Good Eats": "Lifestyle",
    "Shopping": "Lifestyle",
    "SHOPPING": "Lifestyle",
    "Home Improvement": "Lifestyle",
    "House/Garden": "Lifestyle",
    "Health": "Lifestyle",
    "Religious": "Lifestyle",
    "Spiritual": "Lifestyle",
    "Faith": "Lifestyle",
    "INSPIRATION + FAITH": "Lifestyle",
    "MOOD + AMBIANCE": "Lifestyle",
    "Special Interest": "Lifestyle",

    # Australian TV
    "AU Freeview": "Australian TV",
    "AU | Classic": "Australian TV",
    "AU | Drama": "Australian TV",
    "AU | Surfing": "Australian TV",
    "Au": "Australian TV",
    "9Now": "Australian TV",
    "9now": "Australian TV",

    # News (International)
    "DistroTV English & International News": "News",
    "DistroTV All Channels": "Entertainment",
    "DistroTV Food, Travel & More": "Lifestyle",

    # By country prefix (catch-all)
    "EN ESPAÑOL": "Spanish",
    "En Espanol": "Spanish",
    "Español": "Spanish",
    "Spanish": "Spanish",
    "Internacional": "International",
    "International": "International",

    # Specific brands/channels
    "VIDAA": "Entertainment",
    "Veely": "Entertainment",
    "Rewarded.tv🇺🇸": "Entertainment",
    "XUMO🇺🇸": "Entertainment",
    "RakutenTV🇬🇧": "Entertainment",
    "LocalNow🇺🇸": "Entertainment",

    # Default fallback
    "": "Uncategorized",
    "Uncategorized": "Uncategorized",
    "Uncategorized (US)": "Uncategorized",
    "Undefined": "Uncategorized",
    "Other": "Uncategorized",
    "All Channels": "Entertainment",
    "DistroTV All Channels": "Entertainment",
}

# Country prefix mapping for auto-categorization
COUNTRY_PREFIXES = {
    "AE": "Middle East", "AF": "Afghanistan", "AL": "Albania",
    "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica",
    "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "AW": "Aruba", "AZ": "Azerbaijan", "BA": "Bosnia",
    "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium",
    "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BN": "Brunei",
    "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus",
    "BZ": "Belize", "CA": "Canada", "CD": "Congo",
    "CF": "Central African Republic", "CG": "Congo",
    "CH": "Switzerland", "CI": "Cote d'Ivoire",
    "CL": "Chile", "CM": "Cameroon", "CN": "China",
    "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba",
    "CV": "Cape Verde", "CY": "Cyprus", "CZ": "Czech Republic",
    "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark",
    "DM": "Dominica", "DO": "Dominican Republic", "DZ": "Algeria",
    "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt",
    "ER": "Eritrea", "ES": "Spain", "ET": "Ethiopia",
    "FI": "Finland", "FJ": "Fiji", "FR": "France",
    "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada",
    "GE": "Georgia", "GH": "Ghana", "GM": "Gambia",
    "GN": "Guinea", "GR": "Greece", "GT": "Guatemala",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HN": "Honduras",
    "HR": "Croatia", "HT": "Haiti", "HU": "Hungary",
    "ID": "Indonesia", "IE": "Ireland", "IL": "Israel",
    "IN": "India", "IQ": "Iraq", "IR": "Iran",
    "IS": "Iceland", "IT": "Italy", "JM": "Jamaica",
    "JO": "Jordan", "JP": "Japan", "KE": "Kenya",
    "KG": "Kyrgyzstan", "KH": "Cambodia", "KR": "South Korea",
    "KW": "Kuwait", "KZ": "Kazakhstan", "LA": "Laos",
    "LB": "Lebanon", "LK": "Sri Lanka", "LR": "Liberia",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
    "LY": "Libya", "MA": "Morocco", "MC": "Monaco",
    "MD": "Moldova", "ME": "Montenegro", "MG": "Madagascar",
    "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar",
    "MN": "Mongolia", "MO": "Macau", "MT": "Malta",
    "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi",
    "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique",
    "NA": "Namibia", "NE": "Niger", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway",
    "NP": "Nepal", "NZ": "New Zealand", "OM": "Oman",
    "PA": "Panama", "PE": "Peru", "PG": "Papua New Guinea",
    "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal",
    "PY": "Paraguay", "QA": "Qatar", "RO": "Romania",
    "RS": "Serbia", "RU": "Russia", "RW": "Rwanda",
    "SA": "Saudi Arabia", "SD": "Sudan", "SE": "Sweden",
    "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia",
    "SL": "Sierra Leone", "SN": "Senegal", "SO": "Somalia",
    "SR": "Suriname", "SV": "El Salvador", "SY": "Syria",
    "TG": "Togo", "TH": "Thailand", "TN": "Tunisia",
    "TR": "Turkey", "TT": "Trinidad and Tobago",
    "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine",
    "UG": "Uganda", "US": "United States", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VE": "Venezuela", "VN": "Vietnam",
    "YE": "Yemen", "ZA": "South Africa", "ZM": "Zambia",
    "ZW": "Zimbabwe",
}


class Channel:
    """Represents a parsed M3U channel entry."""
    def __init__(self):
        self.tvg_id = ""
        self.tvg_name = ""
        self.tvg_logo = ""
        self.group_title = ""
        self.url = ""
        self.name = ""
        self.raw_extinf = ""
        self.http_user_agent = ""
        self.http_referer = ""
        self.source = ""

    def __repr__(self):
        return f"Channel({self.name}, group={self.group_title})"


def parse_channel_name(raw_name):
    """Strip quality tags and other clutter from channel names."""
    name = raw_name.strip()

    # Remove quality tags: (720p), (1080p), (480p), (240p), (360p), (540p), (270p)
    name = re.sub(r'\s*\(?\d+p\)?\s*', '', name, flags=re.IGNORECASE)

    # Remove HD/SD/FHD/UHD tags
    name = re.sub(r'\s*\(?(HD|SD|FHD|UHD|4K)\)?\s*', '', name, flags=re.IGNORECASE)

    # Remove [Geo-blocked], [Not 24/7], [UK], etc.
    name = re.sub(r'\s*\[.*?\]\s*', ' ', name)

    # Remove quality descriptions after comma: ",1080p" or " (720p)"
    name = re.sub(r',\s*\d+p\s*$', '', name)

    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()

    # Remove trailing/leading commas
    name = name.strip(',').strip()

    return name


def normalize_group(group_title, channel_name=""):
    """Map messy group titles to clean TiviMate categories."""
    if not group_title:
        group_title = ""

    # Direct match
    if group_title in GROUP_MAP:
        return GROUP_MAP[group_title]

    # Case-insensitive match
    lower = group_title.lower()
    for key, value in GROUP_MAP.items():
        if key.lower() == lower:
            return value

    # Check for country prefix (e.g., "BR | Drama" → "Brazil")
    prefix_match = re.match(r'^([A-Z]{2})\s*\|', group_title)
    if prefix_match:
        code = prefix_match.group(1)
        if code in COUNTRY_PREFIXES:
            country = COUNTRY_PREFIXES[code]
            return country

    # Check for brand prefixes (XUMO, LocalNow, RakutenTV, etc.)
    brand_match = re.match(r'^(XUMO|LocalNow|RakutenTV|Rewarded)', group_title, re.IGNORECASE)
    if brand_match:
        brand = brand_match.group(1)
        # Extract the sub-category after the brand
        sub_match = re.match(r'^[^:]+:\s*(.+)', group_title)
        if sub_match:
            sub = sub_match.group(1).strip()
            # Map sub-categories
            sub_lower = sub.lower()
            if sub_lower in ('sports', 'combat sports', 'soccer'):
                return "Sports"
            elif sub_lower in ('news', 'local news'):
                return "News"
            elif sub_lower in ('movies', 'horror & sci-fi', 'westerns & country'):
                return "Movies"
            elif sub_lower in ('kids', 'family and faith', 'faith & family'):
                return "Kids & Family"
            elif sub_lower in ('music', 'music & radio'):
                return "Music"
            elif sub_lower in ('food', 'travel & lifestyle', 'home & design'):
                return "Lifestyle"
            elif sub_lower in ('comedy', 'reality tv', 'classic tv', 'daytime tv',
                               'crime tv', 'entertainment', 'pop culture',
                               'black voices. black stories.', 'latino'):
                return "Entertainment"
            elif sub_lower in ('animals & nature', 'history & learning'):
                return "Documentary"
            elif sub_lower in ('automotive',):
                return "Sports"
        return "Entertainment"

    # Check for DistroTV
    if group_title.startswith("DistroTV"):
        return "Entertainment"

    # Brazilian state codes
    br_states = {
        "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
        "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO",
        "RR", "RS", "SC", "SE", "SP", "TO"
    }
    if group_title in br_states or group_title.upper() in br_states:
        return "Brazil"

    # Brazilian state full names
    br_names = {
        "Alagoas", "Amazonas", "Amapa", "Bahia", "Ceara", "Distrito Federal",
        "Espirito Santo", "Goias", "Maranhao", "Mato Grosso", "Mato Grosso do Sul",
        "Minas Gerais", "Para", "Paraiba", "Parana", "Pernambuco", "Piaui",
        "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondonia",
        "Roraima", "Santa Catarina", "Sao Paulo", "Sergipe", "Tocantins",
        "Amazonas", "Para", "Pb", "Pe", "Pi", "Rj", "Rn", "Rs", "Sc", "Se",
        "Sp", "To", "Ms", "Mt", "Mg", "Df", "Ba", "Go", "Ma"
    }
    for name in br_names:
        if group_title.lower() == name.lower():
            return "Brazil"

    # Country name matching
    for code, country in COUNTRY_PREFIXES.items():
        if group_title.lower() == country.lower():
            return country

    # If group has pipe, it might be a subcategory
    if " | " in group_title:
        parts = group_title.split(" | ", 1)
        if len(parts[0]) == 2 and parts[0].upper() in COUNTRY_PREFIXES:
            return COUNTRY_PREFIXES[parts[0].upper()]

    # Default: keep original but truncate if too long
    if len(group_title) > 30:
        return group_title[:30]

    return group_title


def generate_tvg_id(name):
    """Generate a consistent tvg-id from channel name."""
    # Clean name for tvg-id
    clean = re.sub(r'[^a-zA-Z0-9]', '', name)
    return clean[:30]


def parse_m3u(filepath):
    """Parse an M3U file into Channel objects."""
    channels = []

    try:
        content = Path(filepath).read_text(errors='ignore')
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return channels

    lines = content.strip().split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line.startswith('#EXTINF:'):
            ch = Channel()
            ch.raw_extinf = line

            # Parse attributes
            id_match = re.search(r'tvg-id="([^"]*)"', line)
            if id_match:
                ch.tvg_id = id_match.group(1)

            name_match = re.search(r'tvg-name="([^"]*)"', line)
            if name_match:
                ch.tvg_name = name_match.group(1)

            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            if logo_match:
                ch.tvg_logo = logo_match.group(1)

            group_match = re.search(r'group-title="([^"]*)"', line)
            if group_match:
                ch.group_title = group_match.group(1)

            ua_match = re.search(r'http-user-agent="([^"]*)"', line)
            if ua_match:
                ch.http_user_agent = ua_match.group(1)

            ref_match = re.search(r'http-referrer="([^"]*)"', line)
            if ref_match:
                ch.http_referer = ref_match.group(1)

            # Get channel name (after last comma)
            name_match = re.search(r',\s*(.+)$', line)
            if name_match:
                ch.name = name_match.group(1).strip()

            # Get URL from next line
            if i + 1 < len(lines):
                url_line = lines[i + 1].strip()
                if url_line and not url_line.startswith('#'):
                    ch.url = url_line
                    i += 2
                    channels.append(ch)
                    continue

        i += 1

    return channels


def build_extinf(channel):
    """Build a clean #EXTINF line for a channel."""
    parts = ["#EXTINF:-1"]

    if channel.tvg_id:
        parts.append(f'tvg-id="{channel.tvg_id}"')

    if channel.tvg_name:
        parts.append(f'tvg-name="{channel.tvg_name}"')

    if channel.tvg_logo:
        parts.append(f'tvg-logo="{channel.tvg_logo}"')

    if channel.group_title:
        parts.append(f'group-title="{channel.group_title}"')

    if channel.http_user_agent:
        parts.append(f'http-user-agent="{channel.http_user_agent}"')

    if channel.http_referer:
        parts.append(f'http-referrer="{channel.http_referer}"')

    return f"{' '.join(parts)},{channel.name}"


def normalize_channels(channels):
    """Apply all normalizations to channels."""
    seen_urls = set()
    normalized = []

    for ch in channels:
        # Skip duplicates
        if ch.url in seen_urls:
            continue
        seen_urls.add(ch.url)

        # Skip empty URLs
        if not ch.url:
            continue

        # Skip URLs that aren't HTTP streams
        if not ch.url.startswith(('http://', 'https://')):
            continue

        # Strip quality tags from name
        ch.name = parse_channel_name(ch.name)

        # Skip empty names
        if not ch.name:
            continue

        # Normalize group
        ch.group_title = normalize_group(ch.group_title, ch.name)

        # Add tvg-id if missing
        if not ch.tvg_id:
            ch.tvg_id = generate_tvg_id(ch.name)

        # Add tvg-name if missing
        if not ch.tvg_name:
            ch.tvg_name = ch.name

        normalized.append(ch)

    return normalized


def write_m3u(channels, filepath, title="DJRay IPTV"):
    """Write channels to an M3U file, sorted by group then name."""
    # Group channels
    groups = defaultdict(list)
    for ch in channels:
        groups[ch.group_title].append(ch)

    # Sort groups
    sorted_groups = sorted(groups.keys())

    # Build output
    lines = [
        "#EXTM3U",
        f"# {title}",
        f"# Total channels: {len(channels)}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    for group in sorted_groups:
        group_channels = sorted(groups[group], key=lambda c: c.name.lower())
        lines.append(f"\n# {group} ({len(group_channels)} channels)")
        for ch in group_channels:
            lines.append(build_extinf(ch))
            lines.append(ch.url)

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text('\n'.join(lines) + '\n')
    return len(channels)


def main():
    print("=" * 60)
    print("  DJRay IPTV - M3U Normalizer")
    print("=" * 60)

    # Parse all playlist files
    all_channels = []
    playlist_files = sorted(PLAYLIST_DIR.glob("*.m3u"))

    print(f"\nFound {len(playlist_files)} playlist files")

    for pf in playlist_files:
        channels = parse_m3u(pf)
        # Tag source
        for ch in channels:
            ch.source = pf.stem
        all_channels.extend(channels)
        print(f"  Parsed {pf.name}: {len(channels)} channels")

    print(f"\nTotal raw channels: {len(all_channels)}")

    # Normalize
    print("\nNormalizing...")
    normalized = normalize_channels(all_channels)
    print(f"After dedup/clean: {len(normalized)} channels")

    # Write master M3U
    master_file = OUTPUT_DIR / "master.m3u"
    count = write_m3u(normalized, master_file, "DJRay IPTV Hub")
    print(f"\nMaster M3U: {count} channels → {master_file}")

    # Write per-category M3U files
    print("\nGenerating per-category M3U files...")
    categories = defaultdict(list)
    for ch in normalized:
        categories[ch.group_title].append(ch)

    category_dir = OUTPUT_DIR / "categories"
    category_dir.mkdir(exist_ok=True)

    for group, channels in sorted(categories.items()):
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', group.lower()).strip('_')
        if not safe_name:
            safe_name = "uncategorized"
        cat_file = category_dir / f"{safe_name}.m3u"
        count = write_m3u(channels, cat_file, f"DJRay - {group}")
        print(f"  {group}: {count} channels → {cat_file.name}")

    # Generate EPG from vortexo source (best AU coverage)
    print("\nChecking EPG coverage...")
    epg_file = OUTPUT_DIR / "epg.xml"
    if epg_file.exists():
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(epg_file)
            epg_channels = set()
            for ch in tree.getroot().findall('channel'):
                epg_channels.add(ch.get('id', ''))

            matched = sum(1 for c in normalized if c.tvg_id in epg_channels)
            print(f"  EPG channels: {len(epg_channels)}")
            print(f"  Matched to playlist: {matched}/{len(normalized)} ({matched*100//len(normalized)}%)")
        except Exception as e:
            print(f"  EPG check failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total channels: {len(normalized)}")
    print(f"  Categories: {len(categories)}")
    print(f"  Master M3U: {master_file}")
    print(f"  Category M3Us: {category_dir}/")
    for group, channels in sorted(categories.items(), key=lambda x: -len(x[1])):
        print(f"    {group}: {len(channels)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
