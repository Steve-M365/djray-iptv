#!/usr/bin/env python3
"""
DJRay IPTV - M3U Normalizer v2
Restructures channels into Source → Country → Type hierarchy.
"""

import re
import os
import gzip
from pathlib import Path
from collections import defaultdict
from datetime import datetime

OUTPUT_DIR = Path("output")
PLAYLIST_DIR = OUTPUT_DIR / "playlists"

# ==================== SOURCE MAPPING ====================
# Maps filename prefix to source name
SOURCE_MAP = {
    # Samsung TV Plus
    "ssungaus": ("Samsung TV Plus", "Australia"),
    "ssungbelg": ("Samsung TV Plus", "Belgium"),
    "ssungbra": ("Samsung TV Plus", "Brazil"),
    "ssungden": ("Samsung TV Plus", "Denmark"),
    "ssungfin": ("Samsung TV Plus", "Finland"),
    "ssungire": ("Samsung TV Plus", "Ireland"),
    "ssunglux": ("Samsung TV Plus", "Luxembourg"),
    "ssungmex": ("Samsung TV Plus", "Mexico"),
    "ssungneth": ("Samsung TV Plus", "Netherlands"),
    "ssungnor": ("Samsung TV Plus", "Norway"),
    "ssungnz": ("Samsung TV Plus", "New Zealand"),
    "ssungph": ("Samsung TV Plus", "Philippines"),
    "ssungpor": ("Samsung TV Plus", "Portugal"),
    "ssungsg": ("Samsung TV Plus", "Singapore"),
    "ssungswe": ("Samsung TV Plus", "Sweden"),
    "ssungth": ("Samsung TV Plus", "Thailand"),

    # apsattv country playlists
    "aelg": ("apsattv", "United Arab Emirates"),
    "arlg": ("apsattv", "Argentina"),
    "atlg": ("apsattv", "Austria"),
    "aulg": ("apsattv", "Australia"),
    "belg": ("apsattv", "Belgium"),
    "brlg": ("apsattv", "Brazil"),
    "calg": ("apsattv", "Canada"),
    "chlg": ("apsattv", "Switzerland"),
    "cllg": ("apsattv", "Chile"),
    "colg": ("apsattv", "Colombia"),
    "delg": ("apsattv", "Germany"),
    "dklg": ("apsattv", "Denmark"),
    "eslg": ("apsattv", "Spain"),
    "filg": ("apsattv", "Finland"),
    "frlg": ("apsattv", "France"),
    "gblg": ("apsattv", "United Kingdom"),
    "ielg": ("apsattv", "Ireland"),
    "inlg": ("apsattv", "India"),
    "itlg": ("apsattv", "Italy"),
    "jplg": ("apsattv", "Japan"),
    "krlg": ("apsattv", "South Korea"),
    "lulg": ("apsattv", "Luxembourg"),
    "mxlg": ("apsattv", "Mexico"),
    "nllg": ("apsattv", "Netherlands"),
    "nolg": ("apsattv", "Norway"),
    "nzlg": ("apsattv", "New Zealand"),
    "pelg": ("apsattv", "Poland"),
    "pllg": ("apsattv", "Poland"),
    "ptlg": ("apsattv", "Portugal"),
    "selg": ("apsattv", "Sweden"),
    "sglg": ("apsattv", "Singapore"),
    "uslg": ("apsattv", "United States"),

    # Streaming services (single country or international)
    "daddylive": ("DaddyLive", "International"),
    "daddylive_hd": ("DaddyLive", "International"),
    "daddylive_channels": ("DaddyLive", "International"),
    "daddylive_events": ("DaddyLive", "International"),
    "daddylive_merged": ("DaddyLive", "International"),
    "daddylive_tivimate": ("DaddyLive", "International"),
    "localnow": ("LocalNow", "United States"),
    "whaletvplus_all": ("WhaleTV", "International"),
    "whaletvplus_us": ("WhaleTV", "United States"),
    "tubi_all": ("Tubi", "United States"),
    "distro": ("DistroTV", "International"),
    "freelivesports": ("FreeLiveSports", "United States"),
    "freemoviesplus": ("FreeMoviesPlus", "United States"),
    "freetv": ("FreeTV", "United States"),
    "rewardedtv": ("Rewarded.tv", "United States"),
    "rakuten-jp": ("Rakuten TV", "Japan"),
    "rakutentv-fr": ("Rakuten TV", "France"),
    "rakutentv-uk": ("Rakuten TV", "United Kingdom"),
    "cineverse": ("Cineverse", "United States"),
    "klowd": ("KlowdTV", "United States"),
    "orka": ("Orka TV", "Turkey"),
    "soultv": ("SoulTV", "Brazil"),
    "redeitv": ("RedeiTV", "Brazil"),
    "sportstv": ("SportsTV", "Brazil"),
    "moviearkbr": ("MovieArk", "Brazil"),
    "olhosnatv": ("OlhosnaTV", "Brazil"),
    "igocast": ("IGOCast", "United States"),
    "galxytv": ("Galaxy TV", "United States"),
    "hp": ("HP TV+", "United States"),
    "kogantvplus": ("Kogan TV+", "Australia"),
    "fetchtv": ("Fetch TV", "Australia"),
    "tablo": ("Tablo", "United States"),
    "veely": ("Veely", "United States"),
    "sports_iptvorg": ("iptv-org Sports", "International"),
    "au_iptvorg": ("iptv-org Australia", "Australia"),
    "vortexo_au": ("Vortexo", "Australia"),
    "10fast": ("10FAST", "Australia"),
    "9fast": ("9FAST", "Australia"),
    "freetv": ("FreeTV", "Australia"),
    "cineverse": ("Cineverse", "United States"),
    "firetv": ("Amazon Fire TV", "United States"),
    "xiaomi": ("Xiaomi", "International"),
    "zeasn": ("Zeasn", "International"),
    "metax": ("MetaX", "International"),
    "rok": ("Roku", "United States"),
    "mjh_au_sydney": ("MJH", "Australia"),
    "dearbulut_best": ("dearbulut", None),  # Country from tvg-country attribute
}

# TV platforms with multi-country support (detect country from URL/channel)
MULTI_COUNTRY_SOURCES = {
    "lg.m3u": ("LG Channels", None),  # Country from URL
    "tcl.m3u": ("TCL TV", None),
    "tclbr.m3u": ("TCL TV", "Brazil"),
    "tclplus.m3u": ("TCL TV", None),
    "roku.m3u": ("Roku", "United States"),
    "roku_all.m3u": ("Roku", "United States"),
    "xumo.m3u": ("Xumo", "United States"),
    "vidaam3u": ("Vidaa", "United States"),
    "vizio.m3u": ("Vizio", "United States"),
}

# ==================== COUNTRY DETECTION ====================
# LG URL country codes
LG_COUNTRIES = {
    "ar": "Argentina", "at": "Austria", "au": "Australia", "be": "Belgium",
    "br": "Brazil", "ca": "Canada", "ch": "Switzerland", "cl": "Chile",
    "co": "Colombia", "de": "Germany", "dk": "Denmark", "es": "Spain",
    "fi": "Finland", "fr": "France", "gb": "United Kingdom", "ie": "Ireland",
    "in": "India", "it": "Italy", "jp": "Japan", "kr": "South Korea",
    "mx": "Mexico", "nl": "Netherlands", "no": "Norway", "nz": "New Zealand",
    "pe": "Peru", "ph": "Philippines", "pl": "Poland", "pt": "Portugal",
    "se": "Sweden", "sg": "Singapore", "tr": "Turkey", "tw": "Taiwan",
    "us": "United States", "za": "South Africa",
}

# 2-letter country code to name mapping (for tvg-country attribute)
COUNTRY_CODES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
    "AG": "Antigua and Barbuda", "AL": "Albania", "AM": "Armenia",
    "AO": "Angola", "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso",
    "BG": "Bulgaria", "BH": "Bahrain", "BI": "Burundi", "BJ": "Benin",
    "BN": "Brunei", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Canada", "CD": "Democratic Republic of the Congo",
    "CF": "Central African Republic", "CG": "Congo", "CH": "Switzerland",
    "CI": "Ivory Coast", "CL": "Chile", "CM": "Cameroon", "CN": "China",
    "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "CV": "Cape Verde",
    "CY": "Cyprus", "CZ": "Czech Republic", "DE": "Germany", "DJ": "Djibouti",
    "DK": "Denmark", "DM": "Dominica", "DO": "Dominican Republic", "DZ": "Algeria",
    "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt", "ER": "Eritrea",
    "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji",
    "FR": "France", "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada",
    "GE": "Georgia", "GH": "Ghana", "GM": "Gambia", "GN": "Guinea",
    "GQ": "Equatorial Guinea", "GR": "Greece", "GT": "Guatemala",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HN": "Honduras", "HR": "Croatia",
    "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland",
    "IL": "Israel", "IN": "India", "IQ": "Iraq", "IR": "Iran",
    "IS": "Iceland", "IT": "Italy", "JM": "Jamaica", "JO": "Jordan",
    "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan", "KH": "Cambodia",
    "KI": "Kiribati", "KM": "Comoros", "KN": "Saint Kitts and Nevis",
    "KP": "North Korea", "KR": "South Korea", "KW": "Kuwait",
    "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon", "LC": "Saint Lucia",
    "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya",
    "MA": "Morocco", "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro",
    "MG": "Madagascar", "MK": "North Macedonia", "ML": "Mali",
    "MM": "Myanmar", "MN": "Mongolia", "MR": "Mauritania", "MT": "Malta",
    "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi", "MX": "Mexico",
    "MY": "Malaysia", "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger",
    "NG": "Nigeria", "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway",
    "NP": "Nepal", "NR": "Nauru", "NZ": "New Zealand", "OM": "Oman",
    "PA": "Panama", "PE": "Peru", "PG": "Papua New Guinea", "PH": "Philippines",
    "PK": "Pakistan", "PL": "Poland", "PT": "Portugal", "PY": "Paraguay",
    "QA": "Qatar", "RO": "Romania", "RS": "Serbia", "RU": "Russia",
    "RW": "Rwanda", "SA": "Saudi Arabia", "SB": "Solomon Islands",
    "SC": "Seychelles", "SD": "Sudan", "SE": "Sweden", "SG": "Singapore",
    "SI": "Slovenia", "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somalia", "SR": "Suriname", "SS": "South Sudan",
    "SV": "El Salvador", "SY": "Syria", "SZ": "Eswatini", "TD": "Chad",
    "TG": "Togo", "TH": "Thailand", "TJ": "Tajikistan", "TL": "East Timor",
    "TM": "Turkmenistan", "TN": "Tunisia", "TO": "Tonga",
    "TR": "Turkey", "TT": "Trinidad and Tobago", "TV": "Tuvalu",
    "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine", "UG": "Uganda",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VA": "Vatican City", "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela", "VN": "Vietnam", "VU": "Vanuatu", "WS": "Samoa",
    "XK": "Kosovo", "YE": "Yemen", "ZA": "South Africa", "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

# Channel name country patterns (e.g., "CNN (Australia)")
CHANNEL_COUNTRY_PATTERNS = {
    r'\(australia\)': "Australia",
    r'\(au\)': "Australia",
    r'\(united states?\)': "United States",
    r'\(us\)': "United States",
    r'\(united kingdom\)': "United Kingdom",
    r'\(uk\)': "United Kingdom",
    r'\(france\)': "France",
    r'\(fr\)': "France",
    r'\(germany\)': "Germany",
    r'\(de\)': "Germany",
    r'\(spain\)': "Spain",
    r'\(es\)': "Spain",
    r'\(italy\)': "Italy",
    r'\(it\)': "Italy",
    r'\(brazil\)': "Brazil",
    r'\(br\)': "Brazil",
    r'\(japan\)': "Japan",
    r'\(jp\)': "Japan",
    r'\(india\)': "India",
    r'\(in\)': "India",
    r'\(south korea\)': "South Korea",
    r'\(kr\)': "South Korea",
    r'\(mexico\)': "Mexico",
    r'\(mx\)': "Mexico",
    r'\(canada\)': "Canada",
    r'\(ca\)': "Canada",
    r'\(netherlands\)': "Netherlands",
    r'\(nl\)': "Netherlands",
    r'\(netherland\)': "Netherlands",
    r'\(sweden\)': "Sweden",
    r'\(se\)': "Sweden",
    r'\(norway\)': "Norway",
    r'\(no\)': "Norway",
    r'\(denmark\)': "Denmark",
    r'\(dk\)': "Denmark",
    r'\(finland\)': "Finland",
    r'\(fi\)': "Finland",
    r'\(ireland\)': "Ireland",
    r'\(ie\)': "Ireland",
    r'\(poland\)': "Poland",
    r'\(pl\)': "Poland",
    r'\(portugal\)': "Portugal",
    r'\(pt\)': "Portugal",
    r'\(belgium\)': "Belgium",
    r'\(be\)': "Belgium",
    r'\(switzerland\)': "Switzerland",
    r'\(ch\)': "Switzerland",
    r'\(austria\)': "Austria",
    r'\(at\)': "Austria",
    r'\(new zealand\)': "New Zealand",
    r'\(nz\)': "New Zealand",
    r'\(singapore\)': "Singapore",
    r'\(sg\)': "Singapore",
    r'\(philippines\)': "Philippines",
    r'\(ph\)': "Philippines",
    r'\(thailand\)': "Thailand",
    r'\(th\)': "Thailand",
    r'\(colombia\)': "Colombia",
    r'\(co\)': "Colombia",
    r'\(argentina\)': "Argentina",
    r'\(ar\)': "Argentina",
    r'\(chile\)': "Chile",
    r'\(cl\)': "Chile",
    r'\(turkey\)': "Turkey",
    r'\(tr\)': "Turkey",
    r'\(south africa\)': "South Africa",
    r'\(za\)': "South Africa",
}

# ==================== TYPE DETECTION ====================
# Keywords to detect channel type from name
TYPE_KEYWORDS = {
    "News": [
        "news", "cnn", "bbc", "fox news", "sky news", "reuters", "bloomberg",
        "al jazeera", "msnbc", "newsmax", "oan", "gb news", "euronews",
        "france 24", "dw", "nhk world", "abc news", "cbs news", "nbc news",
        "breaking", "headline", "weather", "accuweather", "weathernation",
    ],
    "Sports": [
        "sports", "espn", "nfl", "nba", "mlb", "nhl", "soccer", "football",
        "cricket", "tennis", "golf", "boxing", "mma", "ufc", "f1", "formula",
        "nascar", "motorsport", "racing", "outdoor", "fishing", "hunting",
        "rugby", "afl", "basketball", "baseball", "hockey", "live events",
        "action sports", "cornhole",
    ],
    "Movies": [
        "movie", "film", "cinema", "flix", "action hits", "comedy hits",
        "horror", "thriller", "western", "classic movies", "b-movies",
        "romance movies", "action movies",
    ],
    "Kids": [
        "kids", "child", "cartoon", "animation", "nickelodeon", "disney",
        "cartoonito", "boomerang", "babytv", "toon", "junior",
    ],
    "Music": [
        "music", "mtv", "vh1", "trace", "karaoke", "vevo", "hitmusic",
        "retro", "oldies", "classic hits", "country music",
    ],
    "Documentary": [
        "doc", "history", "nature", "science", "discovery", "nat geo",
        "animal", "planet", "wildlife", "travel", "adventure earth",
    ],
    "Lifestyle": [
        "food", "cooking", "cuisine", "tasty", "gusto", "travel", "home",
        "garden", "lifestyle", "health", "fitness", "diy", "craft",
        "5 minute crafts", "pet", "animal", "wine",
    ],
    "Entertainment": [
        "entertainment", "comedy", "reality", "game show", "talk show",
        "variety", "drama", "series", "sitcom", "reality tv", "classic tv",
        "123 go", "5 minute crafts", "watchmojo", "failarmy",
    ],
}

# Xumo sub-categories to type mapping
XUMO_TYPES = {
    "news": "News",
    "sports": "Sports",
    "movies": "Movies",
    "crime tv": "Crime",
    "action & drama": "Entertainment",
    "westerns & country": "Entertainment",
    "black voices. black stories.": "Entertainment",
    "kids": "Kids",
    "food & travel": "Lifestyle",
    "home & design": "Lifestyle",
    "comedy": "Entertainment",
    "reality tv": "Entertainment",
    "classic tv": "Entertainment",
    "daytime tv": "Entertainment",
    "animals & nature": "Documentary",
    "history & learning": "Documentary",
}


class Channel:
    """Represents a parsed M3U channel entry."""
    def __init__(self):
        self.tvg_id = ""
        self.tvg_name = ""
        self.tvg_logo = ""
        self.tvg_country = ""
        self.tvg_language = ""
        self.group_title = ""
        self.url = ""
        self.name = ""
        self.raw_extinf = ""
        self.http_user_agent = ""
        self.http_referer = ""
        self.source = ""
        self.source_name = ""
        self.country = ""
        self.channel_type = ""

    def __repr__(self):
        return f"Channel({self.name}, source={self.source_name}, country={self.country}, type={self.channel_type})"


def get_source_info(filename):
    """Get source name and default country from filename."""
    stem = Path(filename).stem.lower()

    # Check direct mapping
    if stem in SOURCE_MAP:
        return SOURCE_MAP[stem]

    # Check multi-country sources
    for pattern, info in MULTI_COUNTRY_SOURCES.items():
        if stem in pattern.lower() or pattern.lower().startswith(stem):
            return info

    # Unknown source - use filename as source name
    return (stem, "Unknown")


def detect_country_from_url(url, channel_name=""):
    """Detect country from URL patterns."""
    # LG URL patterns (lg-au, lg-fr, etc.)
    lg_match = re.search(r'lg-([a-z]{2})', url)
    if lg_match:
        code = lg_match.group(1)
        if code in LG_COUNTRIES:
            return LG_COUNTRIES[code]

    # Samsung URL patterns (samsungau, samsungfr, etc.)
    samsung_match = re.search(r'samsung([a-z]{2,3})', url)
    if samsung_match:
        code = samsung_match.group(1)
        # Map to country
        samsung_map = {
            "au": "Australia", "bra": "Brazil", "fr": "France",
            "de": "Germany", "uk": "United Kingdom", "us": "United States",
            "nl": "Netherlands", "se": "Sweden", "no": "Norway",
            "dk": "Denmark", "fi": "Finland", "ie": "Ireland",
            "it": "Italy", "es": "Spain", "pt": "Portugal",
            "mx": "Mexico", "nz": "New Zealand", "ph": "Philippines",
            "sg": "Singapore", "th": "Thailand", "be": "Belgium",
            "lux": "Luxembourg",
        }
        if code in samsung_map:
            return samsung_map[code]

    return None


def detect_country_from_name(channel_name):
    """Detect country from channel name patterns."""
    for pattern, country in CHANNEL_COUNTRY_PATTERNS.items():
        if re.search(pattern, channel_name, re.IGNORECASE):
            return country
    return None


def detect_type_from_name(channel_name):
    """Detect channel type from name keywords."""
    name_lower = channel_name.lower()

    for channel_type, keywords in TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return channel_type

    return "Entertainment"  # Default


def parse_channel_name(raw_name):
    """Strip quality tags and other clutter from channel names."""
    name = raw_name.strip()

    # Remove quality tags: (720p), (1080p), (480p), etc.
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

            country_match = re.search(r'tvg-country="([^"]*)"', line)
            if country_match:
                ch.tvg_country = country_match.group(1).upper()

            lang_match = re.search(r'tvg-language="([^"]*)"', line)
            if lang_match:
                ch.tvg_language = lang_match.group(1)

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

        # Get source info
        source_name, default_country = get_source_info(ch.source)
        ch.source_name = source_name

        # Detect country (priority: tvg-country > filename > URL > channel name > default)
        country = default_country

        # For dearbulut and similar sources with tvg-country attribute
        if country is None and ch.tvg_country:
            code = ch.tvg_country.upper()
            if code in COUNTRY_CODES:
                country = COUNTRY_CODES[code]

        # For multi-country sources, try URL detection
        if country is None:
            country = detect_country_from_url(ch.url, ch.name)

        # Try channel name detection
        if country is None or country == "Unknown":
            detected = detect_country_from_name(ch.name)
            if detected:
                country = detected

        # Fallback
        if country is None:
            country = "Unknown"

        ch.country = country

        # Detect type from channel name
        ch.channel_type = detect_type_from_name(ch.name)

        # For Xumo, use the sub-category from group-title
        if ch.source_name == "Xumo" and ch.group_title:
            # Extract sub-category after "XUMO🇺🇸: "
            sub_match = re.match(r'XUMO[^:]*:\s*(.+)', ch.group_title, re.IGNORECASE)
            if sub_match:
                sub = sub_match.group(1).strip().lower()
                if sub in XUMO_TYPES:
                    ch.channel_type = XUMO_TYPES[sub]

        # Build new group-title: Source\Country\Type (TiviMate hierarchical)
        ch.group_title = f"{ch.source_name}\\{ch.country}\\{ch.channel_type}"

        # Add tvg-id if missing
        if not ch.tvg_id:
            clean = re.sub(r'[^a-zA-Z0-9]', '', ch.name)
            ch.tvg_id = clean[:30]

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


def write_source_m3u(channels, source_name, filepath):
    """Write channels for a single source to an M3U file."""
    source_channels = [c for c in channels if c.source_name == source_name]
    if not source_channels:
        return 0

    # Group by country
    countries = defaultdict(list)
    for ch in source_channels:
        countries[ch.country].append(ch)

    lines = [
        "#EXTM3U",
        f"# {source_name}",
        f"# Total channels: {len(source_channels)}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    for country in sorted(countries.keys()):
        country_channels = countries[country]
        # Group by type within country
        types = defaultdict(list)
        for ch in country_channels:
            types[ch.channel_type].append(ch)

        for channel_type in sorted(types.keys()):
            type_channels = sorted(types[channel_type], key=lambda c: c.name.lower())
            lines.append(f"\n# {country} | {channel_type} ({len(type_channels)} channels)")
            for ch in type_channels:
                lines.append(build_extinf(ch))
                lines.append(ch.url)

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text('\n'.join(lines) + '\n')
    return len(source_channels)


def main():
    print("=" * 60)
    print("  DJRay IPTV - M3U Normalizer v2")
    print("  Source → Country → Type hierarchy")
    print("=" * 60)

    # Parse all playlist files
    all_channels = []
    playlist_files = sorted(list(PLAYLIST_DIR.glob("*.m3u")) + list(PLAYLIST_DIR.glob("*.m3u8")))

    print(f"\nFound {len(playlist_files)} playlist files")

    for pf in playlist_files:
        channels = parse_m3u(pf)
        # Tag source filename
        for ch in channels:
            ch.source = pf.name
        all_channels.extend(channels)
        print(f"  Parsed {pf.name}: {len(channels)} channels")

    print(f"\nTotal raw channels: {len(all_channels)}")

    # Normalize
    print("\nNormalizing with Source → Country → Type hierarchy...")
    normalized = normalize_channels(all_channels)
    print(f"After dedup/clean: {len(normalized)} channels")

    # Write master M3U
    master_file = OUTPUT_DIR / "master.m3u"
    count = write_m3u(normalized, master_file, "DJRay IPTV Hub")
    print(f"\nMaster M3U: {count} channels → {master_file}")

    # Write per-source M3U files
    print("\nGenerating per-source M3U files...")
    source_dir = OUTPUT_DIR / "sources"
    source_dir.mkdir(exist_ok=True)

    sources = defaultdict(list)
    for ch in normalized:
        sources[ch.source_name].append(ch)

    for source_name, channels in sorted(sources.items(), key=lambda x: -len(x[1])):
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', source_name.lower()).strip('_')
        source_file = source_dir / f"{safe_name}.m3u"
        count = write_source_m3u(channels, source_name, source_file)
        # Show country breakdown
        countries = defaultdict(int)
        for ch in channels:
            countries[ch.country] += 1
        country_str = ", ".join(f"{c}({n})" for c, n in sorted(countries.items(), key=lambda x: -x[1])[:5])
        print(f"  {source_name}: {count} channels → {source_file.name} [{country_str}]")

    # Build sport-specific playlists from EPG
    print("\nBuilding sport-specific playlists...")
    build_sport_playlist(normalized, "formula1", re.compile(r'\b(?:f1|formula\s*1|formula\s*one)\b', re.IGNORECASE))
    build_sport_playlist(normalized, "afl", re.compile(r'\b(?:afl|australian football|footy|7afl|fox footy)\b', re.IGNORECASE),
                         epg_based=True)

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total channels: {len(normalized)}")
    print(f"  Sources: {len(sources)}")
    print(f"  Master M3U: {master_file}")
    print(f"  Source M3Us: {source_dir}/")
    for source_name, channels in sorted(sources.items(), key=lambda x: -len(x[1])):
        countries = set(c.country for c in channels)
        types = set(c.channel_type for c in channels)
        print(f"    {source_name}: {len(channels)} channels ({len(countries)} countries, {len(types)} types)")
    print("=" * 60)


def build_sport_playlist(channels, filename, name_pattern, epg_based=False):
    """Build a sport-specific playlist by matching channel names (and optionally EPG data)."""
    import gzip as gz

    matched = []
    seen_urls = set()

    # Match by channel name
    for ch in channels:
        if name_pattern.search(ch.name) and ch.url not in seen_urls:
            matched.append(ch)
            seen_urls.add(ch.url)

    # For AFL, also match via EPG programme data
    if epg_based:
        epg_file = OUTPUT_DIR / "epg.xml.gz"
        if epg_file.exists():
            try:
                with gz.open(epg_file, "rt") as f:
                    epg = f.read()
                progs = re.findall(
                    r'<programme[^>]*channel="([^"]+)"[^>]*>.*?<title[^>]*>([^<]+)</title>',
                    epg, re.DOTALL
                )
                epg_ids = set()
                for ch_id, title in progs:
                    if name_pattern.search(title):
                        epg_ids.add(ch_id)
                for ch in channels:
                    if hasattr(ch, 'tvg_id') and ch.tvg_id in epg_ids and ch.url not in seen_urls:
                        matched.append(ch)
                        seen_urls.add(ch.url)
            except Exception:
                pass

    out_file = OUTPUT_DIR / "sources" / f"{filename}.m3u"
    with open(out_file, "w") as f:
        f.write("#EXTM3U\n")
        for ch in matched:
            extinf = f'#EXTINF:-1 tvg-id="{ch.tvg_id}" tvg-name="{ch.tvg_name}" tvg-logo="{ch.tvg_logo}" group-title="{ch.source_name}\\{ch.country}\\{ch.channel_type}",{ch.name}'
            f.write(extinf + "\n")
            f.write(ch.url + "\n")

    print(f"  {filename}.m3u: {len(matched)} channels → {out_file.name}")


if __name__ == "__main__":
    main()
