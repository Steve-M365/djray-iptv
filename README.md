# DJRay IPTV

A self-hosted IPTV catalogue: ~22k channels from apsattv.com plus a handful of
additional sources, organised into **flat, TiviMate-friendly groups**, with a
real EPG where free guide data exists.

TiviMate has **no nested groups** — every folder is a single `group-title`. This
project therefore emits one short label per folder (`Australia | Sports`,
`United States | News`, …) and orders the groups so the ones you use appear
first. Anything deeper is done with presets (small, focused playlists).

---

## TiviMate setup

| What | URL |
|---|---|
| Everything | `https://steve-m365.github.io/djray-iptv/output/master.m3u` |
| EPG | `https://steve-m365.github.io/djray-iptv/output/epg.xml.gz` |
| Australia only | `https://steve-m365.github.io/djray-iptv/output/presets/australia.m3u` |
| Sports only | `https://steve-m365.github.io/djray-iptv/output/presets/sports.m3u` |
| Single source | `https://steve-m365.github.io/djray-iptv/output/sources/<source>.m3u` |

1. TiviMate → **Settings → Playlists → Add playlist → M3U URL**, paste a playlist URL.
2. TiviMate → **Settings → EPG → Add EPG**, paste the `epg.xml.gz` URL.
3. In **Manage groups**, hide the folders you never watch — there are ~90.

> These Pages URLs are canonical. Generated playlists are **not committed** to
> `master`; CI rebuilds them daily and publishes to `gh-pages`. `raw.githubusercontent.com`
> URLs for `output/` no longer exist.

---

## What gets generated

```
output/
├── master.m3u          # everything, grouped "<Country> | <Type>"
├── sources/*.m3u       # one file per source, grouped by type
├── presets/*.m3u       # australia, sports, news, movies, kids, us, uk, f1, afl
├── epg.xml.gz          # XMLTV guide, pruned to channels in this catalogue
├── sources.json        # metadata for the web dashboard
├── coverage.json       # EPG coverage per source
└── manifest.json       # per-source fetch/validation results
```

Last local build (15 Nov 2026):

| Metric | Value |
|---|---|
| Sources validated | 116 / 117 playlists |
| Raw channels | 33,372 |
| Published channels | 22,611 |
| Flat groups | 90 (max 3,127, median 159) |
| EPG channels | 3,660 · 212k programmes |
| EPG coverage, all channels | 17.7% |
| EPG coverage, Australia preset | **85%** |
| EPG coverage, Vortexo / Roku | **96.4% / 91.8%** |

Coverage is honest rather than universal: most of this catalogue is FAST
channels, and many FAST services publish no free guide. Mainstream linear
channels (ABC, Sky, CNN, Fox Sports, …) and the Samsung/Pluto/Plex/Roku backed
streams are covered.

---

## How the pipeline works

```
fetch.py  →  output/playlists/*.m3u + manifest.json (validated)
build.py  →  parse → normalise → EPG match → write playlists + metadata
epg.py    →  download guides, match on tvg-id then name, prune, gzip
```

Only `build.py` writes to `output/`. Every other script is either an input
(fetch) or archived (see `legacy/`).

Key behaviours:

- **Validation** — each source must return HTTP 200, non-HTML content and at
  least one `#EXTINF`; failures are listed in `manifest.json`.
- **Junk filtering** — URLs containing `[APP_NAME]`/`[DEVICE_ID]` ad-template
  parameters, non-HTTP entries and empty names are dropped.
- **Deduplication** — exact URLs are collapsed; same-name/same-country channels
  are collapsed *after* EPG matching so the version with guide data wins.
- **Parsing** — `#EXTVLCOPT`, `#EXTGRP` and `#KODIPROP` between `#EXTINF` and
  the URL are preserved rather than treated as end-of-entry.
- **Safety guard** — the build refuses to write anything if it produces fewer
  than 1,000 channels or fewer than 3 working sources, so an upstream outage
  cannot publish an empty playlist.

### Commands

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python build.py              # fetch + build + EPG
python build.py --no-fetch   # re-normalise the existing downloads
python build.py --no-epg     # fast iteration on grouping
./rebuild.sh                 # thin wrapper around build.py

python app.py                # dashboard on http://127.0.0.1:5000
docker compose up -d         # gunicorn, non-root, read-only catalog mount
```

---

## Sources

`sources.json` is the only place to configure inputs.

- **apsattv** — the streams page is scraped on every build, so new playlists are
  picked up automatically. 117 playlists discovered, 116 valid
  (`rakuten-jp.m3u` is a dead link on apsattv).
- **External** — Tubi and Roku playlists are fetched from their upstream repos.
- **Seeds** (`seeds/*.m3u.gz`) — `dearbulut`, `vortexo` and `daddylive` have no
  stable public refresh URL. They are committed snapshots so CI can rebuild.
  Put a URL in `sources.json → external[].url` to refresh them instead.
- **DaddyLive is web-only.** Its entries are `watch.php` player pages, not HLS
  streams. TiviMate cannot play them without a resolver, so they are excluded
  from `master.m3u` and exposed only as
  `output/presets/daddylive-sports.m3u` (224 sports entries, clearly labelled).

Source naming and country detection live in `playlist.py` (`SERVICES`,
`COUNTRY_CODES`, `source_for`). apsattv files are decoded from their naming
scheme: `aulg` → Australia, `ssungaus` → Samsung Australia, `rakuten_fr` →
Rakuten France, and so on.

---

## EPG

Guides come from:

- **epgshare01** per-country rips (AU, NZ, UK, US, CA, IE, ZA, DE, FR, ES, IT,
  BR, IN, SE, NL, PL, PT, DK, NO, FI, AT, CH, MX, AR, CL, CO, PE, JP, KR, TR, GR)
- **i.mjh.nz** aggregated and per-service guides (Samsung TV Plus, Pluto TV,
  Plex, Roku, PBS, plus combined AU/global)

Matching order: exact `tvg-id` → provider-independent core id
(`samsungtvplus-abc123` ↔ `abc123`) → exact normalised display name within the
guide's country. No fuzzy guessing, so a channel either has the correct guide or
no guide. Matched channels are rewritten to the guide's id so players link them.

To add a guide, append to `sources.json → epg.sources`:

```json
{"id": "my-guide", "url": "https://example.com/guide.xml.gz", "countries": ["Australia"]}
```

Use `"id_only": true` for guides whose ids are the only reliable link (no name
matching, avoiding false positives).

---

## Publishing

`.github/workflows/rebuild.yml` runs daily at 15:00 UTC (≈1–2 am Melbourne):

1. runs `pytest`
2. runs `build.py` (fetch, validate, normalise, EPG)
3. copies `docs/index.html`, `docs/setup.html` and `output/` into a `public/` tree
   (excluding raw downloads and the EPG cache)
4. force-pushes that tree to the `gh-pages` branch

Pages is configured as *Deploy from a branch* → `gh-pages` → `/`. Because the
branch is recreated each run, history does not grow with 14 MB guides.

Generated files are deliberately untracked: `output/` is in `.gitignore` and is
only produced by `build.py`. To publish manually, run the **Rebuild catalog**
workflow from the Actions tab.

The Flask app is a convenience for LAN use. It binds `127.0.0.1` by default; the
Docker image sets `HOST=0.0.0.0` behind gunicorn. There is no authentication.

---

## Repository layout

```
app.py                 Flask app (serves catalog, merges selected sources)
build.py               orchestrator + master grouping/presets
fetch.py               apsattv discovery, download, validation, manifest
playlist.py            Channel model, M3U parser, normaliser, writers
epg.py                 guide fetching, id/name matching, pruning
sources.json           source + EPG configuration
seeds/                 committed snapshots for sources without refresh URLs
tests/                 pytest suite (parser, dedupe, grouping, EPG matching)
templates/             Flask dashboard
docs/                  static site published to Pages
legacy/                archived v1 pipeline (isolated output, unsupported)
```

## Tests

```bash
pytest -q     # 15 tests, no network required
```

## Legal

The code is MIT licensed. The playlists, streams and guide data belong to their
respective providers; this repository only aggregates publicly listed links and
is intended for personal use. Publicly redistributing provider streams may
breach their terms of service in your jurisdiction.