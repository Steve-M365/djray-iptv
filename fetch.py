#!/usr/bin/env python3
"""
Download and validate every configured playlist source.

Each playlist is fetched over HTTPS with a browser-like User-Agent, retried on
failure, and validated (not an HTML error page, at least one ``#EXTINF``).
Results are written to ``output/manifest.json`` so the build can refuse to
publish a broken or empty playlist set.
"""

from __future__ import annotations

import gzip
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
PLAYLIST_DIR = ROOT / "output" / "playlists"
MANIFEST = ROOT / "output" / "manifest.json"
SOURCES_CONFIG = ROOT / "sources.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept": "*/*"})

_URL_RE = re.compile(r"https?://[^\s\"'<>]+?\.m3u8?(?:\?[^\s\"'<>]*)?")


@dataclass
class SourceResult:
    id: str
    name: str
    url: str
    origin: str  # "apsattv" | "external" | "seed"
    ok: bool = False
    channels: int = 0
    bytes: int = 0
    status: int | None = None
    error: str = ""
    bytes_on_disk: int = 0


def load_config() -> dict:
    with open(SOURCES_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def _get(url: str, timeout: int = 40, retries: int = 2) -> requests.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 500 and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return resp
        except requests.RequestException as exc:  # pragma: no cover - network
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


def discover_apsattv(url: str) -> list[tuple[str, str]]:
    """Return (id, url) for every .m3u linked from the apsattv streams page."""
    resp = _get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text.replace("\\_", "_").replace("\\/", "/")
    found: dict[str, str] = {}
    for raw in _URL_RE.findall(html):
        clean = raw.rstrip(".,;:)\\\"'")
        name = clean.split("/")[-1].split("?")[0]
        if not name.lower().endswith((".m3u", ".m3u8")):
            continue
        stem = Path(name).stem
        found.setdefault(stem, clean)
    return sorted(found.items())


def _validate_text(text: str) -> tuple[bool, str]:
    if "<html" in text[:400].lower():
        return False, "HTML error page"
    if "#EXTM3U" not in text[:2000].upper() and "#EXTINF" not in text.upper():
        return False, "not an M3U playlist"
    if text.upper().count("#EXTINF") == 0:
        return False, "no channels"
    return True, ""


def fetch_one(source_id: str, name: str, url: str, origin: str) -> SourceResult:
    result = SourceResult(id=source_id, name=name, url=url, origin=origin)
    try:
        resp = _get(url)
        result.status = resp.status_code
        result.bytes = len(resp.content)
        if resp.status_code != 200:
            result.error = f"HTTP {resp.status_code}"
            return result
        text = resp.content.decode("utf-8", errors="ignore")
        ok, why = _validate_text(text)
        if not ok:
            result.error = why
            return result
        result.channels = text.upper().count("#EXTINF")
        dest = PLAYLIST_DIR / f"{source_id}.m3u"
        dest.write_text(text, encoding="utf-8")
        result.ok = True
        result.bytes_on_disk = dest.stat().st_size
    except Exception as exc:  # noqa: BLE001 - report, never crash the fan-out
        result.error = f"{type(exc).__name__}: {exc}"
    return result


def install_seed(source: dict) -> SourceResult:
    """Copy a committed snapshot into the build input directory."""
    seed = ROOT / source.get("seed", "")
    result = SourceResult(
        id=source["id"], name=source.get("name", source["id"]), url="",
        origin="seed",
    )
    if not seed.exists():
        result.error = f"seed missing: {source.get('seed')}"
        return result
    opener = gzip.open if seed.suffix == ".gz" else open
    with opener(seed, "rt", encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    dest = PLAYLIST_DIR / f"{source['id']}.m3u"
    dest.write_text(text, encoding="utf-8")
    result.ok = True
    result.channels = text.upper().count("#EXTINF")
    result.bytes = seed.stat().st_size
    result.bytes_on_disk = dest.stat().st_size
    result.status = 200
    return result


def fetch_all(config: dict, jobs: int = 8) -> list[SourceResult]:
    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
    for old in PLAYLIST_DIR.glob("*.m3u*"):
        old.unlink()

    # De-duplicate by source id; explicit external entries win over scraped ones.
    task_map: dict[str, tuple[str, str, str, str]] = {}
    if config.get("apsattv", {}).get("enabled", True):
        page = config["apsattv"]["url"]
        print(f"Discovering playlists from {page} ...")
        for stem, url in discover_apsattv(page):
            task_map[stem] = (stem, stem, url, "apsattv")

    for entry in config.get("external", []):
        if entry.get("url"):
            task_map[entry["id"]] = (
                entry["id"], entry.get("name", entry["id"]), entry["url"], "external"
            )

    tasks = list(task_map.values())
    print(f"Fetching {len(tasks)} playlists ...")
    results: list[SourceResult] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(fetch_one, *t): t[0] for t in tasks}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            state = f"{res.status}" if res.ok else f"FAIL {res.error}"
            print(f"  {res.id:<24} {state:<28} {res.channels:>6} ch")

    for entry in config.get("external", []):
        if not entry.get("url") and entry.get("seed"):
            res = install_seed(entry)
            results.append(res)
            state = "seed" if res.ok else f"FAIL {res.error}"
            print(f"  {res.id:<24} {state:<28} {res.channels:>6} ch")

    return results


def write_manifest(results: list[SourceResult]) -> dict:
    ok = [r for r in results if r.ok]
    summary = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources_total": len(results),
        "sources_ok": len(ok),
        "sources_failed": len(results) - len(ok),
        "channels": sum(r.channels for r in ok),
        "failed": [
            {"id": r.id, "url": r.url, "error": r.error}
            for r in results
            if not r.ok
        ],
        "sources": [asdict(r) for r in sorted(results, key=lambda r: r.id)],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    config = load_config()
    results = fetch_all(config)
    summary = write_manifest(results)
    print(
        f"\nSources OK: {summary['sources_ok']}/{summary['sources_total']} | "
        f"channels: {summary['channels']}"
    )
    if summary["failed"]:
        print("Failed sources:")
        for item in summary["failed"]:
            print(f"  - {item['id']}: {item['error']}")
    if summary["sources_ok"] == 0:
        print("\nNo playlist could be fetched - build aborted.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())