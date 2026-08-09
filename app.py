#!/usr/bin/env python3
"""
DJRay IPTV Web App - Customizable Playlist Manager
Pick and choose playlists, generate custom M3U, save preferences.
"""

import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

# Paths
OUTPUT_DIR = Path("output")
PLAYLIST_DIR = OUTPUT_DIR / "playlists"
USER_CONFIG = Path("user_config.json")

# Default presets
PRESETS = {
    "f1": {
        "name": "Formula 1 Only",
        "description": "F1 channels from DaddyLive and iptv-org",
        "playlists": ["daddylive_hd"],
        "patterns": ["f1", "formula"]
    },
    "afl": {
        "name": "AFL / Australian Footy",
        "description": "AFL and Australian football channels",
        "playlists": ["au_iptvorg"],
        "patterns": ["afl", "fox footy", "channel 7", "7mate", "channel 9", "channel 10"]
    },
    "sports": {
        "name": "All Sports",
        "description": "Sports channels from all sources",
        "playlists": ["sports_iptvorg", "daddylive_hd"],
        "patterns": []
    },
    "au_tv": {
        "name": "Australian TV",
        "description": "Australian free-to-air and streaming",
        "playlists": ["au_iptvorg", "vortexo_au"],
        "patterns": []
    },
    "daddylive": {
        "name": "DaddyLive Full",
        "description": "All 1270+ DaddyLive 24/7 channels",
        "playlists": ["daddylive_hd"],
        "patterns": []
    },
    "apsattv_all": {
        "name": "apsattv Complete",
        "description": "All 90+ apsattv.com playlists",
        "playlists": ["*"],
        "patterns": []
    },
    "custom": {
        "name": "Custom Selection",
        "description": "Pick your own playlists",
        "playlists": [],
        "patterns": []
    }
}


def load_user_config():
    """Load user preferences."""
    if USER_CONFIG.exists():
        with open(USER_CONFIG) as f:
            return json.load(f)
    return {
        "selected_playlists": [],
        "selected_patterns": [],
        "active_preset": "custom"
    }


def save_user_config(config):
    """Save user preferences."""
    with open(USER_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


def get_available_playlists():
    """Get list of all available playlists with channel counts."""
    playlists = []
    
    if not PLAYLIST_DIR.exists():
        return playlists
    
    for f in sorted(PLAYLIST_DIR.glob("*.m3u")):
        # Count channels
        content = f.read_text(errors='ignore')
        channels = len(re.findall(r'^#EXTINF:', content, re.MULTILINE))
        
        playlists.append({
            "id": f.stem,
            "name": f.stem.replace("_", " ").title(),
            "file": f.name,
            "channels": channels,
            "selected": False
        })
    
    # Add special playlists
    special = [
        {"id": "daddylive_hd", "name": "DaddyLive 24/7", "channels": 1270},
        {"id": "sports_iptvorg", "name": "Sports (iptv-org)", "channels": 493},
        {"id": "au_iptvorg", "name": "Australian TV (iptv-org)", "channels": 79},
        {"id": "vortexo_au", "name": "Australian TV (Vortexo)", "channels": 5676},
    ]
    
    for s in special:
        if not any(p["id"] == s["id"] for p in playlists):
            playlists.insert(0, s)
    
    return playlists


def get_playlist_content(playlist_id):
    """Get content of a specific playlist."""
    # Check for .m3u file
    m3u_file = PLAYLIST_DIR / f"{playlist_id}.m3u"
    if m3u_file.exists():
        return m3u_file.read_text(errors='ignore')
    return None


def build_custom_m3u(config):
    """Build a custom M3U based on user selection."""
    selected = config.get("selected_playlists", [])
    patterns = config.get("selected_patterns", [])
    
    if not selected and not patterns:
        # Return empty playlist
        return "#EXTM3U\n# No playlists selected\n"
    
    lines = ["#EXTM3U", "# Custom Playlist", f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    total_channels = 0
    
    for playlist_id in selected:
        content = get_playlist_content(playlist_id)
        if content:
            # Count channels
            channels = len(re.findall(r'^#EXTINF:', content, re.MULTILINE))
            total_channels += channels
            
            lines.append(f"\n# {playlist_id} ({channels} channels)")
            lines.append(content)
    
    # Filter by patterns if any
    if patterns:
        filtered_lines = []
        for line in lines:
            if line.startswith("#EXTINF:"):
                # Check if channel matches any pattern
                if any(p.lower() in line.lower() for p in patterns):
                    filtered_lines.append(line)
                    # Get the next line (URL)
                    idx = lines.index(line) + 1
                    if idx < len(lines):
                        filtered_lines.append(lines[idx])
            elif not line.startswith("#"):
                filtered_lines.append(line)
        lines = filtered_lines
    
    lines.insert(3, f"# Total channels: {total_channels}")
    return "\n".join(lines)


# ========== ROUTES ==========


@app.route("/")
def index():
    """Main dashboard with playlist selector."""
    playlists = get_available_playlists()
    config = load_user_config()
    return render_template("index.html", playlists=playlists, presets=PRESETS, config=config)


@app.route("/api/playlists")
def api_playlists():
    """Get available playlists."""
    return jsonify(get_available_playlists())


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Get user configuration."""
    return jsonify(load_user_config())


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """Save user configuration."""
    config = request.json
    save_user_config(config)
    return jsonify({"status": "saved"})


@app.route("/api/preset/<preset_id>", methods=["POST"])
def api_apply_preset(preset_id):
    """Apply a preset configuration."""
    if preset_id not in PRESETS:
        return jsonify({"error": "Invalid preset"}), 400
    
    preset = PRESETS[preset_id]
    config = load_user_config()
    config["selected_playlists"] = preset.get("playlists", [])
    config["selected_patterns"] = preset.get("patterns", [])
    config["active_preset"] = preset_id
    save_user_config(config)
    return jsonify({"status": "applied", "preset": preset})


@app.route("/playlist/custom.m3u")
@app.route("/custom.m3u")
def serve_custom_m3u():
    """Serve custom M3U based on user selection."""
    config = load_user_config()
    m3u_content = build_custom_m3u(config)
    
    return m3u_content, 200, {
        "Content-Type": "audio/x-mpegurl",
        "Content-Disposition": "attachment; filename=custom_playlist.m3u"
    }


@app.route("/playlist/master.m3u")
@app.route("/master.m3u")
def serve_master_m3u():
    """Serve the full master M3U."""
    master_file = OUTPUT_DIR / "master.m3u"
    if master_file.exists():
        return send_file(master_file, mimetype="audio/x-mpegurl")
    return "#EXTM3U\n# No master playlist available\n", 200, {"Content-Type": "audio/x-mpegurl"}


@app.route("/epg/epg.xml")
@app.route("/epg.xml")
def serve_epg():
    """Serve the EPG XML."""
    epg_file = OUTPUT_DIR / "epg.xml"
    if epg_file.exists():
        return send_file(epg_file, mimetype="application/xml")
    return "# No EPG available\n", 404


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Preview a playlist before selecting."""
    data = request.json
    playlist_id = data.get("playlist_id")
    
    content = get_playlist_content(playlist_id)
    if content:
        # Extract first 20 channels
        lines = content.split("\n")
        preview_lines = []
        count = 0
        for line in lines:
            preview_lines.append(line)
            if line.startswith("#EXTINF:"):
                count += 1
                if count >= 20:
                    break
        
        return jsonify({
            "id": playlist_id,
            "content": "\n".join(preview_lines),
            "total_channels": len(re.findall(r'^#EXTINF:', content, re.MULTILINE))
        })
    
    return jsonify({"error": "Playlist not found"}), 404


@app.route("/copy-url/<path:url_type>")
def copy_url(url_type):
    """Return copyable URL for TiviMate."""
    base_url = request.host_url.rstrip("/")
    
    if url_type == "m3u":
        return jsonify({"url": f"{base_url}/playlist/custom.m3u"})
    elif url_type == "m3u_full":
        return jsonify({"url": f"{base_url}/playlist/master.m3u"})
    elif url_type == "epg":
        return jsonify({"url": f"{base_url}/epg/epg.xml"})
    else:
        return jsonify({"error": "Invalid URL type"}), 400


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
    
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"\n{'='*60}")
    print(f"DJRay IPTV Hub - Customizable Playlist Manager")
    print(f"{'='*60}")
    print(f"Dashboard:  http://localhost:{port}")
    print(f"Custom M3U: http://localhost:{port}/playlist/custom.m3u")
    print(f"Full M3U:   http://localhost:{port}/playlist/master.m3u")
    print(f"EPG:        http://localhost:{port}/epg/epg.xml")
    print(f"{'='*60}\n")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
