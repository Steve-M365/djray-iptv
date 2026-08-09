# M3U Normalizer Restructure Plan

## Goal
Restructure from flat categories to **Source → Country → Type** hierarchy.

## Current Issues
- Samsung/LG files have NO group-title (country in filename/URL)
- apsattv country files have useless group-title
- 9,133 channels in "Uncategorized"

## New Structure

```
▼ Samsung TV Plus
    ▼ Australia
        Sky News
        Entertainment Hub
    ▼ Brazil
        ...
    ▼ France
        ...
    ▼ Germany
        ...
    (16 countries)
▼ LG Channels
    ▼ Australia
        123 Go English
    ▼ Argentina
        123 Go Spanish
    ▼ France
        LG 1
        Sony One
    (multi-country from lg.m3u)
▼ Xumo
    ▼ United States
        ▼ News
            CBS News
            NBC News
        ▼ Sports
            Outdoor America
▼ Vidaa
    ▼ United States
        ...
▼ Roku
    ▼ United States
        ...
▼ LocalNow
    ▼ United States
        ...
▼ WhaleTV
    ▼ International
        ...
    ▼ United States
        ...
▼ DaddyLive
    ▼ Sports
        Live events
▼ apsattv Australia
    ▼ Entertainment
        ...
    ▼ News
        ...
▼ apsattv France
    ▼ Entertainment
        ...
▼ Tubi
    ▼ United States
        ...
▼ DistroTV
    ▼ International
        ...
```

## Source Mappings

### TV Platform Sources (by filename prefix)
| Filename | Source Name | Country Detection |
|----------|-------------|-------------------|
| `ssungaus.m3u` | Samsung TV Plus | Filename: aus=Australia |
| `ssungbra.m3u` | Samsung TV Plus | Filename: bra=Brazil |
| `ssungneth.m3u` | Samsung TV Plus | Filename: neth=Netherlands |
| `lg.m3u` | LG Channels | URL: lg-au, lg-fr, etc. |
| `frlg.m3u` | LG Channels (FR) | Filename: frlg=France |
| `tcl.m3u` | TCL TV | URL: tcl-xx or channel name |
| `roku.m3u` | Roku | Default: United States |
| `xumo.m3u` | Xumo | Group: XUMO🇺🇸: News |
| `vidaam3u` | Vidaa | Default: United States |
| `vizio.m3u` | Vizio | Default: United States |
| `tablo.m3u` | Tablo | Default: United States |
| `xiaomi.m3u` | Xiaomi | URL/channel name |
| `firetv.m3u` | Amazon Fire TV | Default: United States |
| `hp.m3u` | HP TV+ | Default: United States |
| `kogantvplus.m3u` | Kogan TV+ | Default: Australia |
| `galxytv.m3u` | Galaxy TV | Default: United States |
| `fetchtv.m3u` | Fetch TV | Default: Australia |
| `veely.m3u` | Veely | Default: United States |
| `metax.m3u` | MetaX | URL/channel name |

### Country Playlist Sources (apsattv.com)
| Filename | Source Name | Country |
|----------|-------------|---------|
| `aulg.m3u` | apsattv Australia | Australia |
| `uslg.m3u` | apsattv United States | United States |
| `frlg.m3u` | apsattv France | France |
| `delg.m3u` | apsattv Germany | Germany |
| `eslg.m3u` | apsattv Spain | Spain |
| `itlg.m3u` | apsattv Italy | Italy |
| `brlg.m3u` | apsattv Brazil | Brazil |
| ... | ... | ... |

### Streaming Service Sources
| Filename | Source Name | Default Country |
|----------|-------------|-----------------|
| `daddylive_hd.m3u8` | DaddyLive | International |
| `localnow.m3u` | LocalNow | United States |
| `whaletvplus_all.m3u` | WhaleTV | International |
| `whaletvplus_us.m3u` | WhaleTV | United States |
| `tubi_all.m3u` | Tubi | United States |
| `distro.m3u` | DistroTV | International |
| `freelivesports.m3u` | FreeLiveSports | United States |
| `rewardedtv.m3u` | Rewarded.tv | United States |
| `rakuten-jp.m3u` | Rakuten TV | Japan |
| `rakutentv-fr.m3u` | Rakuten TV | France |
| `rakutentv-uk.m3u` | Rakuten TV | United Kingdom |
| `cineverse.m3u` | Cineverse | United States |
| `klowd.m3u` | KlowdTV | United States |
| `orka.m3u` | Orka TV | Turkey |
| `soultv.m3u` | SoulTV | Brazil |
| `redeitv.m3u` | RedeiTV | Brazil |
| `sportstv.m3u` | SportsTV | Brazil |

### Sports Sources
| Filename | Source Name | Notes |
|----------|-------------|-------|
| `sports_iptvorg.m3u` | iptv-org Sports | International |
| `freelivesports.m3u` | FreeLiveSports | US-focused |
| `sportstv.m3u` | SportsTV | Brazil |

## Country Code Mapping

```python
# Samsung filename → Country
SAMSUNG_COUNTRIES = {
    "aus": "Australia",
    "belg": "Belgium",
    "bra": "Brazil",
    "den": "Denmark",
    "fin": "Finland",
    "ire": "Ireland",
    "lux": "Luxembourg",
    "mex": "Mexico",
    "neth": "Netherlands",
    "nor": "Norway",
    "nz": "New Zealand",
    "ph": "Philippines",
    "por": "Portugal",
    "sg": "Singapore",
    "swe": "Sweden",
    "th": "Thailand",
}

# LG URL → Country
LG_COUNTRIES = {
    "lg-ar": "Argentina",
    "lg-at": "Austria",
    "lg-au": "Australia",
    "lg-be": "Belgium",
    "lg-br": "Brazil",
    "lg-ca": "Canada",
    "lg-ch": "Switzerland",
    "lg-cl": "Chile",
    "lg-co": "Colombia",
    "lg-de": "Germany",
    "lg-dk": "Denmark",
    "lg-es": "Spain",
    "lg-fi": "Finland",
    "lg-fr": "France",
    "lg-gb": "United Kingdom",
    "lg-ie": "Ireland",
    "lg-in": "India",
    "lg-it": "Italy",
    "lg-jp": "Japan",
    "lg-kr": "South Korea",
    "lg-mx": "Mexico",
    "lg-nl": "Netherlands",
    "lg-no": "Norway",
    "lg-nz": "New Zealand",
    "lg-pe": "Peru",
    "lg-ph": "Philippines",
    "lg-pl": "Poland",
    "lg-pt": "Portugal",
    "lg-se": "Sweden",
    "lg-sg": "Singapore",
    "lg-tr": "Turkey",
    "lg-tw": "Taiwan",
    "lg-us": "United States",
    "lg-za": "South Africa",
}

# apsattv filename → Country
APSATTV_COUNTRIES = {
    "aulg": "Australia",
    "uslg": "United States",
    "uklg": "United Kingdom",
    "frlg": "France",
    "delg": "Germany",
    "eslg": "Spain",
    "itlg": "Italy",
    "ptlg": "Portugal",
    "belg": "Belgium",
    "nllg": "Netherlands",
    "dklg": "Denmark",
    "nolg": "Norway",
    "selg": "Sweden",
    "filg": "Finland",
    "ielg": "Ireland",
    "chlg": "Switzerland",
    "atlg": "Austria",
    "pelg": "Poland",
    "brlg": "Brazil",
    "mxlg": "Mexico",
    "colg": "Colombia",
    "arlg": "Argentina",
    "cllg": "Chile",
    "inlg": "India",
    "krlg": "South Korea",
    "jplg": "Japan",
    "nzlg": "New Zealand",
    "sglg": "Singapore",
    "lulg": "Luxembourg",
}
```

## Type Detection

For channels without a useful group-title, detect type from:
1. **Channel name keywords** (e.g., "News" → News, "Sports" → Sports)
2. **URL patterns** (e.g., "news" in URL → News)
3. **Default to Entertainment** if no match

```python
TYPE_KEYWORDS = {
    "News": ["news", "cnn", "bbc", "fox news", "sky news", "reuters", "bloomberg"],
    "Sports": ["sports", "espn", "nfl", "nba", "mlb", "nhl", "soccer", "football", "cricket", "tennis"],
    "Movies": ["movie", "film", "cinema", "flix", "action hits", "comedy hits"],
    "Kids": ["kids", "child", "cartoon", "animation", "nickelodeon", "disney"],
    "Music": ["music", "mtv", "vh1", "trace", "karaoke"],
    "Documentary": ["doc", "history", "nature", "science", "discovery", "nat geo"],
    "Lifestyle": ["food", "cooking", "travel", "home", "garden", "lifestyle"],
}
```

## Implementation

1. **Parse source from filename** (e.g., `ssungaus.m3u` → "Samsung TV Plus")
2. **Detect country** from filename/URL/channel-name
3. **Detect type** from channel name keywords
4. **Build group-title** as "Source | Country | Type" (e.g., "Samsung TV Plus | Australia | News")
5. **Write per-source M3U files** in `output/sources/` directory
6. **Keep master.m3u** with the new hierarchical groups

## Output Structure

```
output/
├── master.m3u                    # All channels with Source | Country | Type groups
├── epg.xml.gz                    # EPG data
├── categories/                   # Per-category M3U (flat)
│   ├── news.m3u
│   ├── sports.m3u
│   ├── entertainment.m3u
│   └── ...
└── sources/                      # Per-source M3U (hierarchical)
    ├── samsung_tv_plus.m3u
    ├── lg_channels.m3u
    ├── xumo.m3u
    ├── vidaa.m3u
    ├── roku.m3u
    ├── localnow.m3u
    ├── tubi.m3u
    └── ...
```

## TiviMate Integration

Users can add:
- `master.m3u` — all channels with groups
- Or individual source files from `output/sources/`
