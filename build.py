#!/usr/bin/env python3
"""
Build the DJRay IPTV catalog.

Pipeline (single writer for every output file):

    fetch.py  -> output/playlists/*.m3u + output/manifest.json
    build.py  -> parse -> normalise -> EPG match -> output/master.m3u,
                 output/sources/*.m3u, output/presets/*.m3u,
                 output/epg.xml.gz, output/sources.json, output/coverage.json

Nothing is written unless the build produced a sane channel count, so a broken
upstream source can never publish an empty or truncated master playlist.

Usage:
    python3 build.py                # fetch + build + EPG
    python3 build.py --no-fetch     # rebuild from the existing downloads
    python3 build.py --no-epg       # skip the guide (fast local iteration)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import fetch
import playlist as pl

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
PLAYLIST_DIR = OUTPUT / "playlists"
SOURCES_DIR = OUTPUT / "sources"
PRESETS_DIR = OUTPUT / "presets"
MASTER = OUTPUT / "master.m3u"
SOURCES_META = OUTPUT / "sources.json"
CONFIG_PATH = ROOT / "sources.json"

MIN_CHANNELS = 1000
MIN_SOURCES = 3


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_playlists(config: dict) -> tuple[list[pl.Channel], dict[str, dict], set[str]]:
    """Parse every downloaded playlist. Returns channels, source metadata, web-only ids."""
    external = {e["id"]: e for e in config.get("external", [])}
    web_only = {sid for sid, e in external.items() if e.get("web_only")}
    channels: list[pl.Channel] = []
    meta: dict[str, dict] = {}

    files = sorted(PLAYLIST_DIR.glob("*.m3u*"))
    if not files:
        print(f"ERROR: no playlists in {PLAYLIST_DIR}. Run fetch.py first.")
        sys.exit(1)

    for path in files:
        source_id = path.stem
        name, default_country = pl.source_for(source_id)
        entry = external.get(source_id)
        if entry:
            name = entry.get("name") or name
            default_country = entry.get("country") or default_country
        text = path.read_text(encoding="utf-8", errors="ignore")
        parsed = pl.parse_playlist(text, source_id, name, default_country or "")
        meta[source_id] = {
            "id": source_id,
            "name": name,
            "file": f"sources/{pl.slug(name)}.m3u",
            "channels_raw": len(parsed),
            "web_only": source_id in web_only,
        }
        channels.extend(parsed)

    return channels, meta, web_only


def fold_for_master(channels: list[pl.Channel], country_min: int = 150, type_min: int = 40) -> list[pl.Channel]:
    """Keep the master's group list usable on a TV remote.

    Countries with fewer than ``country_min`` channels are folded into
    "Other Countries". A country's channel types with fewer than ``type_min``
    entries are folded into that country's Entertainment group. Per-source and
    preset playlists stay unfiltered.
    """
    from collections import Counter
    import copy

    country_counts = Counter(c.country for c in channels)
    group_counts = Counter((c.country, c.ctype) for c in channels)
    out = []
    for ch in channels:
        ch = copy.copy(ch)
        if country_counts[ch.country] < country_min:
            ch.country = "Other Countries"
        if group_counts[(ch.country, ch.ctype)] < type_min:
            ch.ctype = "Entertainment"
        out.append(ch)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DJRay IPTV playlists and EPG")
    parser.add_argument("--no-fetch", action="store_true", help="reuse output/playlists")
    parser.add_argument("--no-epg", action="store_true", help="skip EPG generation")
    parser.add_argument("--fetch-only", action="store_true", help="download and validate sources only")
    parser.add_argument("--min-channels", type=int, default=MIN_CHANNELS)
    args = parser.parse_args()

    started = time.time()
    config = load_config()

    # 1. Fetch / validate sources -------------------------------------------------
    if not args.no_fetch:
        results = fetch.fetch_all(config)
        summary = fetch.write_manifest(results)
        print(
            f"\nFetched {summary['sources_ok']}/{summary['sources_total']} sources, "
            f"{summary['channels']} raw channels"
        )
        if summary["sources_ok"] < MIN_SOURCES:
            print("ERROR: too few sources succeeded - refusing to build.")
            return 1
    if args.fetch_only:
        return 0

    # 2. Parse + normalise ---------------------------------------------------------
    channels, meta, web_only = load_playlists(config)
    print(f"Parsed {len(channels)} raw channel entries from {len(meta)} sources")
    channels = pl.normalise(channels, web_only=web_only)
    print(f"Normalised: {len(channels)} unique playable channels")

    if len(channels) < args.min_channels:
        print(
            f"ERROR: only {len(channels)} channels after normalisation "
            f"(minimum {args.min_channels}). Nothing written."
        )
        return 1

    # 3. EPG -----------------------------------------------------------------------
    coverage = {}
    if not args.no_epg:
        import epg

        print("Matching EPG ...")
        coverage = epg.build_epg(channels, config)

    # Always collapse same-name/same-country duplicates; when EPG ran, the
    # copy with guide data wins.
    before = len(channels)
    channels = pl.dedupe_named(channels)
    print(f"De-duplicated by name: {before - len(channels)} removed")
    if not args.no_epg:
        coverage = epg.finalise(channels)

    # 4. Write everything -----------------------------------------------------------
    master_channels = [c for c in channels if c.source_id not in web_only]
    master_channels = fold_for_master(master_channels)
    print(f"Writing master playlist ({len(master_channels)} channels, web-only sources excluded)")
    count = pl.write_playlist(
        master_channels, MASTER, title="DJRay IPTV Hub", grouping="country"
    )

    source_counts = pl.write_source_playlists(channels, SOURCES_DIR)
    print(f"Wrote {len(source_counts)} per-source playlists")

    preset_counts: dict[str, int] = {}
    for name, spec in pl.PRESETS.items():
        selected = pl.build_preset(name, spec, channels)
        if not selected:
            continue
        preset_counts[name] = pl.write_playlist(
            selected,
            PRESETS_DIR / f"{name}.m3u",
            title=spec["title"],
            grouping="type",
        )
    print(f"Wrote {len(preset_counts)} presets")

    # 5. Metadata for the dashboard ------------------------------------------------
    aggregated: dict[str, dict] = {}
    for source_id, info in meta.items():
        items = [c for c in channels if c.source_id == source_id]
        if not items:
            continue
        name = info["name"]
        row = aggregated.setdefault(name, {
            "name": name,
            "file": f"sources/{pl.slug(name)}.m3u",
            "channels": 0,
            "countries": set(),
            "types": set(),
            "web_only": info.get("web_only", False),
            "coverage_pct": coverage.get("by_source", {}).get(name, {}).get("coverage_pct", 0.0),
        })
        row["channels"] += len(items)
        row["countries"].update(c.country for c in items)
        row["types"].update(c.ctype for c in items)

    sources_meta = []
    for row in sorted(aggregated.values(), key=lambda r: -r["channels"]):
        row["countries"] = sorted(row["countries"])
        row["types"] = sorted(row["types"])
        sources_meta.append(row)

    SOURCES_META.write_text(
        json.dumps(
            {
                "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "master_channels": count,
                "sources": sources_meta,
                "presets": preset_counts,
                "coverage": coverage,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    elapsed = time.time() - started
    print("\n" + "=" * 60)
    print(f"  DONE in {elapsed:.0f}s")
    print(f"  master.m3u       {count:>7} channels")
    print(f"  sources          {len(source_counts):>7} files")
    print(f"  presets          {len(preset_counts):>7} files")
    print(f"  EPG coverage     {coverage.get('coverage_pct', 0):>7}%")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())