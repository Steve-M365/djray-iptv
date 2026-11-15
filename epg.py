#!/usr/bin/env python3
"""
Real EPG builder.

Downloads XMLTV guides, matches them against the channels we publish, rewrites
each channel's ``tvg-id`` to the guide id, and writes a pruned gzipped guide
containing only the channels we actually carry.

Matching is conservative, in this order:
  1. exact ``tvg-id``
  2. ``tvg-id`` without its country suffix (``ABCPerth`` vs ``ABCPerth.au``)
  3. exact normalised display name, restricted to the guide's countries
Everything else is left without a guide rather than given a wrong one.
"""

from __future__ import annotations

import gzip
import io
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from playlist import Channel

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
EPG_GZ = OUTPUT / "epg.xml.gz"
COVERAGE = OUTPUT / "coverage.json"
CACHE = OUTPUT / "epg-cache"

UA = "Mozilla/5.0 (compatible; djray-iptv/2.0; +https://github.com/Steve-M365/djray-iptv)"
_QUALITY = re.compile(r"\b(fhd|uhd|4k|hd|sd|1080p|720p)\b", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9]+")
_SUFFIX = re.compile(r"\.[a-z]{2,3}$")
_SERVICES = ("samsungtvplus", "plutotv", "plex", "roku", "stirr", "tubi", "xumo",
             "vizio", "lg", "tcl", "sling", "pbs", "distrotv")
_PLEX_HASH = re.compile(r"^[0-9a-f]{24}-")


def normalise(name: str) -> str:
    name = (name or "").lower()
    name = re.sub(r"^\s*(au|uk|us|ca|nz|ie)\s*[:\-]\s*", "", name)
    name = re.sub(r"\s*\([^)]*\)\s*$", " ", name)  # trailing "(Australia)"
    name = _QUALITY.sub(" ", name)
    name = name.replace("&", " and ")
    name = _NON_WORD.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    # "Sky News TV" -> "sky news"; keep short names intact.
    for suffix in (" tv", " channel", " network"):
        if name.endswith(suffix) and len(name) - len(suffix) >= 6:
            name = name[: -len(suffix)].strip()
    return name


def _base_id(value: str) -> str:
    return _SUFFIX.sub("", value).lower()


def _core_id(value: str) -> str:
    """Provider-independent id: 'samsungtvplus-atbd3700001eh' -> 'atbd3700001eh'."""
    v = value.lower().split("@")[0]
    v = _SUFFIX.sub("", v)
    for prefix in _SERVICES:
        if v.startswith(prefix + "-"):
            v = v[len(prefix) + 1:]
            break
    return _PLEX_HASH.sub("", v)


def _service_of(value: str) -> str:
    v = value.lower()
    for prefix in _SERVICES:
        if v.startswith(prefix + "-"):
            return prefix
    return ""


class Matcher:
    def __init__(self, channels: list[Channel]) -> None:
        self.by_id: dict[str, list[Channel]] = defaultdict(list)
        self.by_base: dict[str, list[Channel]] = defaultdict(list)
        self.by_name: dict[str, list[Channel]] = defaultdict(list)
        self.by_core: dict[str, list[Channel]] = defaultdict(list)
        for ch in channels:
            if ch.tvg_id:
                self.by_id[ch.tvg_id.lower()].append(ch)
                self.by_base[_base_id(ch.tvg_id)].append(ch)
                self.by_core[_core_id(ch.tvg_id)].append(ch)
            for candidate in {normalise(ch.name), normalise(ch.tvg_name)}:
                if candidate:
                    self.by_name[candidate].append(ch)

    def match(self, ch_id: str, display_names: list[str], countries: list[str], allow_names: bool = True):
        found: list[Channel] = []
        found.extend(self.by_id.get(ch_id.lower(), []))
        found.extend(self.by_base.get(_base_id(ch_id), []))
        service = _service_of(ch_id)
        core = _core_id(ch_id)
        for ch in self.by_core.get(core, []):
            if service and not ch.tvg_id.lower().startswith(service + "-"):
                continue
            found.append(ch)
        for dn in display_names if allow_names else []:
            key = normalise(dn)
            for ch in self.by_name.get(key, []):
                if countries and ch.country not in countries:
                    continue
                found.append(ch)
        for dn in []:
            key = normalise(dn)
            key = normalise(dn)
            for ch in self.by_name.get(key, []):
                if countries and ch.country not in countries:
                    continue
                found.append(ch)
        # de-duplicate while preserving order
        seen: set[int] = set()
        unique: list[Channel] = []
        for ch in found:
            if id(ch) not in seen:
                seen.add(id(ch))
                unique.append(ch)
        return unique


def _download(url: str, dest: Path, timeout: int = 90) -> bytes:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and time.time() - dest.stat().st_mtime < 6 * 3600:
        return dest.read_bytes()
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    resp.raise_for_status()
    data = resp.content
    if not data:
        raise ValueError("empty response")
    dest.write_bytes(data)
    return data


def _xml_bytes(data: bytes) -> bytes:
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def _in_window(start: str, lo: datetime, hi: datetime) -> bool:
    if not start or len(start) < 12:
        return False
    try:
        dt = datetime.strptime(start[:12], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return lo <= dt <= hi


def build_epg(channels: list[Channel], config: dict) -> dict:
    sources = [s for s in config.get("epg", {}).get("sources", []) if s.get("url")]
    matcher = Matcher(channels)
    matched_urls: dict[str, str] = {}
    wanted: set[str] = set()
    keep_channels: list[ET.Element] = []
    programmes: list[ET.Element] = []
    window_lo = datetime.now(timezone.utc) - timedelta(days=1)
    window_hi = datetime.now(timezone.utc) + timedelta(days=7)

    for src in sources:
        try:
            raw = _download(src["url"], CACHE / f"{src['id']}.xml.gz")
            data = _xml_bytes(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"  EPG {src['id']}: FAILED ({type(exc).__name__}: {exc})")
            continue

        countries = src.get("countries", [])
        seen_ids: set[str] = set()
        try:
            for _, elem in ET.iterparse(io.BytesIO(data), events=("end",)):
                tag = elem.tag.rsplit("}", 1)[-1]
                if tag == "channel":
                    ch_id = elem.get("id") or ""
                    names = [dn.text or "" for dn in elem.findall("display-name")]
                    hits = matcher.match(
                        ch_id, names, countries, allow_names=not src.get("id_only")
                    ) if ch_id else []
                    if hits and ch_id not in seen_ids:
                        seen_ids.add(ch_id)
                        wanted.add(ch_id)
                        for ch in hits:
                            matched_urls[ch.url] = ch_id
                            ch.tvg_id = ch_id
                            ch.epg_matched = True
                        keep_channels.append(elem)
                    else:
                        elem.clear()
                elif tag == "programme":
                    ch_id = elem.get("channel") or ""
                    if ch_id in wanted and _in_window(elem.get("start", ""), window_lo, window_hi):
                        programmes.append(ET.fromstring(ET.tostring(elem, encoding="utf-8")))
                    elem.clear()
        except ET.ParseError as exc:
            print(f"  EPG {src['id']}: parse error ({exc})")

        print(f"  EPG {src['id']}: {len(data) / 1e6:.1f} MB parsed, {len(wanted)} ids matched so far")

    root = ET.Element("tv", {"generator-info-name": "DJRay IPTV Hub"})
    kept: set[str] = set()
    for elem in keep_channels:
        cid = elem.get("id")
        if cid and cid not in kept:
            kept.add(cid)
            root.append(elem)
    for prog in programmes:
        root.append(prog)

    tmp = OUTPUT / "epg.xml.gz.tmp"
    with gzip.open(tmp, "wb", compresslevel=6) as fh:
        fh.write(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    tmp.replace(EPG_GZ)

    report = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epg_channels": len(kept),
        "programmes": len(programmes),
        "matched_channels": len(matched_urls),
        "total_channels": len(channels),
        "coverage_pct": round(100 * len(matched_urls) / max(1, len(channels)), 1),
        "by_source": _coverage(channels, matched_urls),
    }
    COVERAGE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"  EPG written: {len(kept)} channels, {len(programmes)} programmes, "
        f"{report['coverage_pct']}% of the playlist has a guide"
    )
    return report


def finalise(channels: list[Channel]) -> dict:
    """Prune the written guide to the channels that survived de-duplication."""
    ids = {c.tvg_id for c in channels if c.epg_matched and c.tvg_id}
    with gzip.open(EPG_GZ, "rb") as fh:
        root = ET.parse(fh).getroot()
    pruned = ET.Element("tv", dict(root.attrib))
    for elem in root.findall("channel"):
        if elem.get("id") in ids:
            pruned.append(elem)
    programmes = 0
    for elem in root.findall("programme"):
        if elem.get("channel") in ids:
            pruned.append(elem)
            programmes += 1

    tmp = OUTPUT / "epg.xml.gz.tmp"
    with gzip.open(tmp, "wb", compresslevel=6) as fh:
        fh.write(ET.tostring(pruned, encoding="utf-8", xml_declaration=True))
    tmp.replace(EPG_GZ)

    matched = {c.url for c in channels if c.epg_matched}
    report = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epg_channels": len(pruned.findall("channel")),
        "programmes": programmes,
        "matched_channels": len(matched),
        "total_channels": len(channels),
        "coverage_pct": round(100 * len(matched) / max(1, len(channels)), 1),
        "by_source": _coverage(channels, matched),
    }
    COVERAGE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"  Guide pruned: {report['epg_channels']} channels, {programmes} programmes "
        f"({report['coverage_pct']}% coverage)"
    )
    return report


def _coverage(channels: list[Channel], matched: set[str] | dict) -> dict:
    totals: dict[str, dict] = {}
    for ch in channels:
        row = totals.setdefault(ch.source, {"channels": 0, "matched": 0})
        row["channels"] += 1
        if ch.url in matched:
            row["matched"] += 1
    for row in totals.values():
        row["coverage_pct"] = round(100 * row["matched"] / max(1, row["channels"]), 1)
    return dict(sorted(totals.items(), key=lambda kv: -kv[1]["channels"]))