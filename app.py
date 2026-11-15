#!/usr/bin/env python3
"""
DJRay IPTV web app.

Serves the generated catalog and builds merged playlists on demand:

  /                       dashboard
  /api/sources            source metadata (generated)
  /custom.m3u?sources=a,b merged playlist for the chosen sources
  /presets/<name>.m3u     pre-built preset
  /master.m3u             everything
  /epg.xml                gzipped XMLTV guide
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
SOURCES_DIR = OUTPUT / "sources"
PRESETS_DIR = OUTPUT / "presets"
SOURCES_META = OUTPUT / "sources.json"
USER_CONFIG = ROOT / "user_config.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def load_meta() -> dict:
    if not SOURCES_META.exists():
        return {"sources": [], "presets": {}, "coverage": {}, "master_channels": 0}
    return json.loads(SOURCES_META.read_text(encoding="utf-8"))


def load_user_config() -> dict:
    default = {"selected_sources": [], "selected_preset": ""}
    if USER_CONFIG.exists():
        try:
            data = json.loads(USER_CONFIG.read_text(encoding="utf-8"))
            return {k: data.get(k, v) for k, v in default.items()}
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_user_config(config: dict) -> None:
    clean = {
        "selected_sources": [
            s[:80] for s in config.get("selected_sources", [])[:50] if isinstance(s, str)
        ],
        "selected_preset": (
            config["selected_preset"][:50]
            if isinstance(config.get("selected_preset"), str)
            else ""
        ),
    }
    USER_CONFIG.write_text(json.dumps(clean, indent=2), encoding="utf-8")


def valid_source(stem: str) -> Path | None:
    """Resolve a source id to a file, rejecting path traversal."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", stem or ""):
        return None
    path = SOURCES_DIR / f"{stem}.m3u"
    return path if path.is_file() else None


def merge_playlists(paths: list[Path]) -> str:
    lines = ["#EXTM3U", "# DJRay IPTV merged playlist"]
    seen: set[str] = set()
    total = 0
    for path in paths:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.upper().startswith(("#EXTM3U", "# DJRAY", "# TOTAL", "# GROUPS", "# REGENERATED")):
                continue
            if line.startswith("#"):
                lines.append(line)
            elif line.lower().startswith(("http://", "https://")):
                if line not in seen:
                    seen.add(line)
                    lines.append(line)
                    total += 1
            else:
                lines.append(line)
    lines.insert(2, f"# Total channels: {total}")
    return "\n".join(lines) + "\n"


def m3u_response(body: str, filename: str):
    return body, 200, {
        "Content-Type": "audio/x-mpegurl",
        "Content-Disposition": f"attachment; filename={filename}",
    }


@app.get("/")
def index():
    meta = load_meta()
    return render_template(
        "index.html",
        meta=meta,
        config=load_user_config(),
    )


@app.get("/api/sources")
def api_sources():
    return jsonify(load_meta())


@app.get("/api/config")
def api_get_config():
    return jsonify(load_user_config())


@app.post("/api/config")
def api_save_config():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "invalid JSON"}), 400
    save_user_config(payload)
    return jsonify({"status": "saved"})


@app.get("/custom.m3u")
def serve_custom():
    requested = [s for s in request.args.get("sources", "").split(",") if s]
    preset = request.args.get("preset", "")
    if preset:
        path = PRESETS_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '', preset)}.m3u"
        if path.is_file():
            return send_file(path, mimetype="audio/x-mpegurl")
        abort(404)
    if not requested:
        requested = load_user_config().get("selected_sources", [])
    paths = [p for p in (valid_source(s) for s in requested) if p]
    if not paths:
        abort(404)
    return m3u_response(merge_playlists(paths), "djray-custom.m3u")


@app.get("/presets/<name>.m3u")
def serve_preset(name: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        abort(404)
    path = PRESETS_DIR / f"{name}.m3u"
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="audio/x-mpegurl")


@app.get("/master.m3u")
@app.get("/playlist/master.m3u")
def serve_master():
    path = OUTPUT / "master.m3u"
    if path.is_file():
        return send_file(path, mimetype="audio/x-mpegurl")
    abort(404)


@app.get("/epg.xml")
@app.get("/epg/epg.xml")
def serve_epg():
    for name, mime in (("epg.xml.gz", "application/gzip"), ("epg.xml", "application/xml")):
        path = OUTPUT / name
        if path.is_file():
            return send_file(path, mimetype=mime, as_attachment=False)
    abort(404)


@app.get("/output/<path:name>")
def serve_output(name: str):
    target = (OUTPUT / name).resolve()
    if OUTPUT.resolve() not in target.parents or not target.is_file():
        abort(404)
    return send_file(target)


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print(f"DJRay IPTV: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)