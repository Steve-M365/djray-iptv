#!/usr/bin/env python3
"""
Playlist model, parsing, normalisation and writing for DJRay IPTV.

Design goals
------------
* TiviMate friendly: TiviMate has FLAT groups (no nesting), so every
  ``group-title`` is a single, short, sortable label (``Australia | Sports``).
* One writer for each output file. Only this module emits playlists.
* Defensive parsing: comments between ``#EXTINF`` and the URL
  (``#EXTVLCOPT``, ``#EXTGRP``, ``#KODIPROP``) are preserved, not skipped.
* Junk links (``[APP_NAME]`` template parameters, non-HTTP entries) are dropped
  so players do not show channels that can never play.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Countries
# ---------------------------------------------------------------------------

COUNTRY_CODES = {
    "ad": "Andorra", "ae": "United Arab Emirates", "al": "Albania",
    "ar": "Argentina", "at": "Austria", "au": "Australia", "ba": "Bosnia",
    "be": "Belgium", "bg": "Bulgaria", "br": "Brazil", "ca": "Canada",
    "ch": "Switzerland", "cl": "Chile", "cn": "China", "co": "Colombia",
    "cz": "Czech Republic", "de": "Germany", "dk": "Denmark", "ee": "Estonia",
    "es": "Spain", "fi": "Finland", "fr": "France", "gb": "United Kingdom",
    "gr": "Greece", "hr": "Croatia", "hu": "Hungary", "ie": "Ireland",
    "in": "India", "it": "Italy", "jp": "Japan", "kr": "South Korea",
    "lt": "Lithuania", "lu": "Luxembourg", "lv": "Latvia", "mx": "Mexico",
    "nl": "Netherlands", "no": "Norway", "nz": "New Zealand", "pe": "Peru",
    "ph": "Philippines", "pl": "Poland", "pt": "Portugal", "ro": "Romania",
    "rs": "Serbia", "sa": "Saudi Arabia", "se": "Sweden", "sg": "Singapore",
    "si": "Slovenia", "sk": "Slovakia", "th": "Thailand", "tr": "Turkey",
    "tw": "Taiwan", "uk": "United Kingdom", "us": "United States",
    "za": "South Africa",
}

# Samsung TV Plus three-letter marketplace suffixes
SAMSUNG_CODES = {
    "aus": "Australia", "belg": "Belgium", "bra": "Brazil", "den": "Denmark",
    "fin": "Finland", "ire": "Ireland", "lux": "Luxembourg", "mex": "Mexico",
    "neth": "Netherlands", "nor": "Norway", "nz": "New Zealand",
    "ph": "Philippines", "por": "Portugal", "sg": "Singapore",
    "swe": "Sweden", "th": "Thailand",
}

# Preferred group ordering in the master playlist. TiviMate honours the order
# channels first appear in the file when "Groups sorting = by order in playlist".
COUNTRY_ORDER = [
    "Australia", "New Zealand", "International", "United States",
    "United Kingdom", "Canada", "Ireland", "Other Countries",
]

# Short labels for TV UIs; TiviMate truncates long group names.
COUNTRY_LABELS = {
    "United States": "US",
    "United Kingdom": "UK",
    "New Zealand": "NZ",
    "Other Countries": "Other",
    "United Arab Emirates": "UAE",
    "South Africa": "SA",
    "Dominican Republic": "DR",
    "Papua New Guinea": "PNG",
}
COUNTRY_LABEL_TO_NAME = {v: k for k, v in COUNTRY_LABELS.items()}
COUNTRY_LABEL_TO_NAME.update({k: k for k in COUNTRY_ORDER})
TYPE_ORDER = [
    "Sports", "News", "Movies", "Kids", "Music", "Documentary",
    "Lifestyle", "Entertainment", "Other",
]

# ---------------------------------------------------------------------------
# Source catalogue
# ---------------------------------------------------------------------------

# Explicit source definitions keyed by playlist stem (filename without .m3u).
SERVICES: dict[str, tuple[str, str | None]] = {
    # Australian / NZ
    "10fast": ("10 FAST", "Australia"),
    "9fast": ("9Now FAST", "Australia"),
    "kogantvplus": ("Kogan TV+", "Australia"),
    "fetchtv": ("Fetch TV", "Australia"),
    "freetv": ("FreeTV", "International"),
    # Platform / device
    "firetv": ("Amazon Fire TV", "United States"),
    "xiaomi": ("Xiaomi", "International"),
    "vizio": ("Vizio WatchFree+", "United States"),
    "tcl": ("TCL TV", "International"),
    "tclbr": ("TCL TV", "Brazil"),
    "tclplus": ("TCL TV", "International"),
    "xumo": ("Xumo Play", "United States"),
    "zeasn": ("Zeasn", "International"),
    "metax": ("MetaX", "International"),
    "roku": ("Roku Channel", "United States"),
    "rok": ("Roku Channel", "United States"),
    "roku_all": ("Roku Channel", "United States"),
    "vidaa": ("Vidaa", "United States"),
    "lg": ("LG Channels", "International"),
    "whaletvplus": ("WhaleTV", "International"),
    "whaletvplus_all": ("WhaleTV", "International"),
    "whaletvplus_us": ("WhaleTV", "United States"),
    # Content / services
    "distro": ("DistroTV", "International"),
    "freelivesports": ("FreeLiveSports", "United States"),
    "freemoviesplus": ("FreeMoviesPlus", "United States"),
    "tubi": ("Tubi", "United States"),
    "tubi_all": ("Tubi", "United States"),
    "localnow": ("LocalNow", "United States"),
    "hp": ("HP TV+", "United States"),
    "klowd": ("KlowdTV", "United States"),
    "galxytv": ("Galaxy TV", "United States"),
    "igocast": ("IGOCast", "United States"),
    "tablo": ("Tablo", "United States"),
    "veely": ("Veely", "United States"),
    "cineverse": ("Cineverse", "United States"),
    "rewardedtv": ("Rewarded.tv", "United States"),
    "sportstv": ("SportsTV", "Brazil"),
    # Regional / country
    "moviearkbr": ("MovieArk", "Brazil"),
    "redeitv": ("RedeiTV", "Brazil"),
    "soultv": ("SoulTV", "Brazil"),
    "olhosnatv": ("OlhosnaTV", "Brazil"),
    "orka": ("Orka TV", "Turkey"),
    # Aggregators
    "apsattv": ("apsattv", "International"),
    "dearbulut": ("dearbulut", "International"),
    "vortexo": ("Vortexo", "United States"),
    "daddylive": ("DaddyLive", "International"),
    "vidaa_": ("Vidaa", "United States"),
}

# Sources that only expose a web player (not a direct HLS stream). They are
# excluded from the master playlist by default; see sources.json.
WEB_ONLY_SOURCES = {"daddylive"}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')
_PLACEHOLDER_RE = re.compile(r"[\[\]{}]")
_QUALITY_RE = re.compile(
    r"\s*[\(\[]?\b(?:fhd|uhd|4k|1080p|720p|576p|480p|hd|sd)\b[\)\]]?\s*",
    re.IGNORECASE,
)
_BRACKETS_RE = re.compile(r"\s*\[[^\]]*\]\s*")
_COUNTRY_NAME_RE = re.compile(r"\(([a-z ]{2,20})\)\s*$", re.IGNORECASE)


@dataclass
class Channel:
    name: str
    url: str
    source: str = ""
    source_id: str = ""
    tvg_id: str = ""
    tvg_name: str = ""
    logo: str = ""
    country: str = ""
    tvg_country: str = ""
    default_country: str = ""
    ctype: str = ""
    group_hint: str = ""
    extras: list[str] = field(default_factory=list)  # EXTVLCOPT / KODIPROP
    user_agent: str = ""
    referrer: str = ""
    epg_id: str = ""
    epg_matched: bool = False

    @property
    def unique_key(self) -> str:
        return self.url.strip()


def _split_extinf(line: str) -> tuple[str, str]:
    """Split '#EXTINF:...,Name' honouring commas inside quoted attributes."""
    body = line[len("#EXTINF:"):]
    in_quote = False
    for i, ch in enumerate(body):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            return body[:i], body[i + 1:].strip()
    return body, ""


def parse_playlist(
    text: str,
    source_id: str,
    source_name: str = "",
    default_country: str = "",
) -> list[Channel]:
    """Parse an M3U document into channels, tolerating player comments."""
    channels: list[Channel] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    pending: Channel | None = None

    while i < len(lines):
        line = lines[i].strip()
        if line.upper().startswith("#EXTINF:"):
            head, name = _split_extinf(line)
            attrs = dict(_ATTR_RE.findall(head))
            pending = Channel(
                name=name,
                url="",
                source=source_name or source_id,
                source_id=source_id,
                tvg_id=attrs.get("tvg-id", "").strip(),
                tvg_name=attrs.get("tvg-name", "").strip(),
                logo=attrs.get("tvg-logo", "").strip(),
                group_hint=attrs.get("group-title", "").strip(),
                tvg_country=COUNTRY_CODES.get(attrs.get("tvg-country", "").lower(), ""),
                default_country=default_country,
            )
            pending.user_agent = attrs.get("http-user-agent", "")
            pending.referrer = attrs.get("http-referrer") or attrs.get("http-referer", "")
            i += 1
            continue

        if pending is not None:
            if line.startswith("#"):
                # Player options belong to the next URL, keep them.
                if line.upper().startswith(("#EXTVLCOPT", "#EXTGRP", "#KODIPROP")):
                    pending.extras.append(line)
                i += 1
                continue
            if line:
                pending.url = line
                channels.append(pending)
                pending = None
        i += 1

    return channels


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def source_for(stem: str) -> tuple[str, str | None]:
    """Best-effort (source name, default country) for an apsattv filename."""
    stem = stem.lower()
    if stem in SERVICES:
        return SERVICES[stem]

    # apsattv country playlists: aelg, aulg, gblg, uslg ...
    m = re.fullmatch(r"([a-z]{2})lg", stem)
    if m and m.group(1) in COUNTRY_CODES:
        return "apsattv", COUNTRY_CODES[m.group(1)]

    # Samsung TV Plus marketplaces
    m = re.fullmatch(r"ssung([a-z]{2,4})", stem)
    if m and m.group(1) in SAMSUNG_CODES:
        return "Samsung TV Plus", SAMSUNG_CODES[m.group(1)]

    # Rakuten TV marketplaces
    m = re.fullmatch(r"rakuten[_-]([a-z]{2})", stem)
    if m and m.group(1) in COUNTRY_CODES:
        return "Rakuten TV", COUNTRY_CODES[m.group(1)]

    # WhaleTV countries
    m = re.fullmatch(r"whaletvplus_([a-z]{2})", stem)
    if m and m.group(1) in COUNTRY_CODES:
        return "WhaleTV", COUNTRY_CODES[m.group(1)]

    # Fall back to a tidied filename.
    pretty = stem.replace("_", " ").replace("-", " ").title()
    return pretty, None


def clean_name(name: str) -> str:
    name = _BRACKETS_RE.sub(" ", name or "")
    name = _QUALITY_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" ,-|")
    return name.strip()


def slug(text: str, limit: int = 40) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return out[:limit]


def infer_country(ch: Channel) -> str:
    if ch.tvg_country:
        return ch.tvg_country
    # Seed files carry "Source | Country | Type" and are more specific than a
    # source-wide default (Vortexo carries mostly Australian channels).
    parts = [p.strip() for p in ch.group_hint.split("|")]
    if len(parts) >= 3 and parts[1] and parts[1].lower() != "unknown":
        return parts[1]
    if ch.default_country:
        return ch.default_country
    # "CNN (Australia)"
    m = _COUNTRY_NAME_RE.search(ch.name)
    if m:
        name = m.group(1).strip().lower()
        for code, country in COUNTRY_CODES.items():
            if country.lower() == name:
                return country
    m = re.search(r"lg-([a-z]{2})", ch.url)
    if m and m.group(1) in COUNTRY_CODES:
        return COUNTRY_CODES[m.group(1)]
    return "International"


TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Sports": (
        "sport", "espn", "nfl", "nba", "mlb", "nhl", "soccer", "football",
        "cricket", "tennis", "golf", "boxing", "mma", "ufc", "f1", "formula",
        "nascar", "motorsport", "racing", "rugby", "afl", "basketball",
        "baseball", "hockey", "fight", "wrestling", "olympics", "darts",
        "snooker", "cycling", "surfing", "skate", "extreme", "poker",
    ),
    "News": (
        "news", "cnn", "bbc news", "fox news", "sky news", "reuters",
        "bloomberg", "al jazeera", "msnbc", "newsmax", "gb news", "euronews",
        "france 24", "dw ", "nhk", "abc news", "cbs news", "nbc news",
        "weather", "accuweather", "headline", "breaking",
    ),
    "Movies": (
        "movie", "film", "cinema", "flix", "horror", "thriller", "western",
        "classic movies", "b-movies", "romance", "action hits", "drama movie",
        "cinema", "picture", "screams", "noir",
    ),
    "Kids": (
        "kids", "child", "cartoon", "animation", "nickelodeon", "nick",
        "disney", "cartoonito", "boomerang", "babytv", "toon", "junior",
        "pbs kids", "moonbug", "teletubbies", "pokemon", "barbie",
    ),
    "Music": (
        "music", "mtv", "vh1", "trace", "karaoke", "vevo", "hits", "oldies",
        "country music", "concerts", "radio", "clubbing", "dance",
    ),
    "Documentary": (
        "doc", "history", "nature", "science", "discovery", "nat geo",
        "animal", "planet", "wildlife", "earth", "universe", "crime",
        "investigation", "explore", "smithsonian",
    ),
    "Lifestyle": (
        "food", "cook", "cuisine", "tasty", "gusto", "travel", "home",
        "garden", "lifestyle", "health", "fitness", "diy", "craft", "pet",
        "wine", "fashion", "beauty", "house", "hunt", "fish", "motor",
    ),
    "Entertainment": (
        "entertainment", "comedy", "reality", "game show", "talk", "variety",
        "series", "sitcom", "classic tv", "failarmy", "watchmojo", "prank",
        "drama", "soap", "telenovela", "novela", "laugh", "funny",
    ),
}


def dedupe_named(channels: list[Channel]) -> list[Channel]:
    """Collapse same-name/same-country channels, preferring ones with EPG data."""
    best: dict[tuple[str, str], Channel] = {}
    order: list[tuple[str, str]] = []
    for ch in channels:
        key = (ch.name.lower(), ch.country)
        if key not in best:
            best[key] = ch
            order.append(key)
        elif ch.epg_matched and not best[key].epg_matched:
            best[key] = ch
    return [best[k] for k in order]


def infer_type(ch: Channel) -> str:
    hint = ch.group_hint
    parts = [p.strip() for p in hint.split("|")]
    if len(parts) >= 3 and parts[2]:
        for t in TYPE_ORDER:
            if parts[2].lower() == t.lower():
                return t
        if parts[2]:
            return parts[2].title()
    name = ch.name.lower()
    for ctype, words in TYPE_KEYWORDS.items():
        if any(w in name for w in words):
            return ctype
    return "Entertainment"


def country_label(country: str) -> str:
    return COUNTRY_LABELS.get(country, country)


def group_country(ch: Channel) -> str:
    """TiviMate flat group: 'Country | Type', with a short country label."""
    return f"{country_label(ch.country)} | {ch.ctype}"


def group_type(ch: Channel) -> str:
    return ch.ctype


# ---------------------------------------------------------------------------
# Normalisation pipeline
# ---------------------------------------------------------------------------

def normalise(channels: Iterable[Channel], *, web_only: set[str] | None = None) -> list[Channel]:
    """Clean, de-duplicate and classify channels. Order is preserved."""
    web_only = web_only or WEB_ONLY_SOURCES
    seen_urls: set[str] = set()
    out: list[Channel] = []

    for ch in channels:
        url = (ch.url or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            continue
        if _PLACEHOLDER_RE.search(url):
            # [APP_NAME] / [DEVICE_ID] style ad-template params never resolve.
            continue
        if " " in url:
            continue

        name = clean_name(ch.name or ch.tvg_name)
        if not name or len(name) < 2:
            continue

        # De-duplicate streams by URL. Name collisions are resolved *after*
        # EPG matching so the version with guide data wins.
        if url in seen_urls:
            continue
        country = infer_country(ch)
        seen_urls.add(url)

        ch.name = name
        ch.tvg_name = ch.tvg_name or name
        ch.country = country
        ch.ctype = infer_type(ch)
        ch.epg_id = ch.tvg_id
        if not ch.tvg_id:
            ch.tvg_id = f"{slug(ch.source_id or ch.source)}.{slug(name)}"
        if ch.extras:
            ch.extras = [e for e in ch.extras if not e.upper().startswith("#EXTGRP")]
        out.append(ch)

    return out


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _extinf(ch: Channel, group: str) -> str:
    attrs = [f'tvg-id="{ch.tvg_id}"', f'tvg-name="{ch.tvg_name}"']
    if ch.logo:
        attrs.append(f'tvg-logo="{ch.logo}"')
    attrs.append(f'group-title="{group}"')
    if ch.user_agent:
        attrs.append(f'http-user-agent="{ch.user_agent}"')
    if ch.referrer:
        attrs.append(f'http-referrer="{ch.referrer}"')
    return f"#EXTINF:-1 {' '.join(attrs)},{ch.name}"


def sort_groups(channels: list[Channel], grouping: str = "country") -> list[Channel]:
    """Order channels so TiviMate shows groups in a curated order."""
    def order(ch: Channel) -> tuple:
        country = ch.country
        cidx = COUNTRY_ORDER.index(country) if country in COUNTRY_ORDER else len(COUNTRY_ORDER)
        tidx = TYPE_ORDER.index(ch.ctype) if ch.ctype in TYPE_ORDER else len(TYPE_ORDER)
        return (cidx, country.lower(), tidx, ch.name.lower())

    return sorted(channels, key=order)


def _group_key(ch: Channel, grouping: str, split_large: int) -> str:
    if grouping != "country":
        return group_type(ch)
    return group_country(ch)


def write_playlist(
    channels: list[Channel],
    path: Path,
    *,
    title: str,
    grouping: str = "country",
    total_label: str = "Total channels",
    split_large: int = 1500,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    base: dict[str, list[Channel]] = defaultdict(list)
    for ch in channels:
        base[_group_key(ch, grouping, split_large)].append(ch)

    groups: dict[str, list[Channel]] = {}
    for key, members in base.items():
        if grouping == "country" and len(members) > split_large:
            # A single 5,000-channel folder is unusable on a TV remote, so split
            # it by source while keeping the flat two-part label.
            for ch in members:
                groups.setdefault(f"{key} \u00b7 {ch.source}", []).append(ch)
        else:
            groups[key] = members

    lines = [
        "#EXTM3U",
        f"# {title}",
        f"# {total_label}: {len(channels)}",
        "# Groups are flat (TiviMate does not support nested groups).",
        "# Regenerated by build.py - do not edit by hand.",
    ]
    for group in _sorted_groups(groups, grouping):
        members = sorted(groups[group], key=lambda c: c.name.lower())
        lines.append("")
        lines.append(f"# {group} ({len(members)} channels)")
        for ch in members:
            lines.append(_extinf(ch, group))
            lines.extend(ch.extras)
            lines.append(ch.url)

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)
    return len(channels)


def _sorted_groups(groups: dict[str, list[Channel]], grouping: str) -> list[str]:
    def key(g: str) -> tuple:
        if grouping == "country":
            head = g.split(" \u00b7 ")[0]
            label, _, ctype = head.partition(" | ")
            country = COUNTRY_LABEL_TO_NAME.get(label, label)
            cidx = COUNTRY_ORDER.index(country) if country in COUNTRY_ORDER else len(COUNTRY_ORDER)
            tidx = TYPE_ORDER.index(ctype) if ctype in TYPE_ORDER else len(TYPE_ORDER)
            return (cidx, label.lower(), tidx, g.lower())
        idx = TYPE_ORDER.index(g) if g in TYPE_ORDER else len(TYPE_ORDER)
        return (idx, g.lower())

    return sorted(groups, key=key)


def write_source_playlists(channels: list[Channel], out_dir: Path) -> dict[str, int]:
    """One playlist per source, grouped by channel type."""
    by_source: dict[str, list[Channel]] = defaultdict(list)
    for ch in channels:
        by_source[ch.source].append(ch)

    counts: dict[str, int] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.m3u"):
        stale.unlink()
    for source, items in sorted(by_source.items()):
        filename = f"{slug(source)}.m3u"
        write_playlist(
            items,
            out_dir / filename,
            title=source,
            grouping="country",
            total_label="Total channels",
        )
        counts[filename] = len(items)
    return counts


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "australia": {
        "title": "Australia - all channels",
        "countries": ["Australia", "New Zealand"],
    },
    "sports": {"title": "All sports", "types": ["Sports"]},
    "news": {"title": "All news", "types": ["News"]},
    "movies": {"title": "All movies", "types": ["Movies"]},
    "kids": {"title": "All kids", "types": ["Kids"]},
    "us": {"title": "United States", "countries": ["United States"], "types": None},
    "uk": {"title": "United Kingdom", "countries": ["United Kingdom"]},
    "f1": {"title": "Formula 1", "name_regex": r"\b(f1|formula\s*(1|one))\b"},
    "afl": {"title": "AFL", "name_regex": r"(afl|australian football|footy|fox footy)"},
    "daddylive-sports": {
        "title": "DaddyLive sports (web player required)",
        "sources": ["DaddyLive"],
        "types": ["Sports"],
        "allow_web_only": True,
    },
}


def build_preset(name: str, spec: dict, channels: list[Channel]) -> list[Channel]:
    selected = channels
    if spec.get("countries"):
        selected = [c for c in selected if c.country in spec["countries"]]
    if spec.get("types"):
        selected = [c for c in selected if c.ctype in spec["types"]]
    if spec.get("sources"):
        selected = [c for c in selected if c.source in spec["sources"]]
    if spec.get("name_regex"):
        rx = re.compile(spec["name_regex"], re.IGNORECASE)
        selected = [c for c in selected if rx.search(c.name)]
    return selected