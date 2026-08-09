#!/usr/bin/env python3
"""
Apsattv IPTV Web App
Serves M3U playlists and EPG for TiviMate and other IPTV players.
"""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file
from apscheduler.schedulers.background import BackgroundScheduler

from main import (
    CACHE_DIR,
    CATEGORY_ORDER,
    CHANNEL_LIST,
    CONFIG_FILE,
    EPG_FILE,
    EXTERNAL_PLAYLISTS,
    MASTER_M3U,
    OUTPUT_DIR,
    categorize_playlist,
    extract_playlist_urls,
    fetch_m3u_content_with_retry,
    fetch_page,
    generate_master_m3u,
    load_config,
    parse_m3u_channels,
    process_single_playlist,
    save_channel_index,
    APSV_URL,
)
from epg_generator import (
    fetch_epgshare,
    fetch_iptvorg_epg,
    fetch_manual_epg,
    filter_epg_by_channels,
    load_channels,
    write_epg,
)

app = Flask(__name__)

# Global state
last_refresh = None
refresh_in_progress = False
channel_count = 0
playlist_count = 0


def load_stats():
    """Load stats from output files."""
    global last_refresh, channel_count, playlist_count

    if CHANNEL_LIST.exists():
        with open(CHANNEL_LIST) as f:
            channels = json.load(f)
            channel_count = len(channels)

    if MASTER_M3U.exists():
        with open(MASTER_M3U) as f:
            content = f.read()
            playlist_count = content.count("# Playlist:")

    if MASTER_M3U.exists():
        last_refresh = datetime.fromtimestamp(MASTER_M3U.stat().st_mtime)


def refresh_playlists():
    """Background refresh of playlists and EPG."""
    global refresh_in_progress
    if refresh_in_progress:
        return {"status": "already_running"}

    refresh_in_progress = True
    try:
        print(f"[{datetime.now()}] Starting playlist refresh...")

        # 1. Fetch and generate master M3U
        config = load_config()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        html = fetch_page(APSV_URL)
        urls_with_names = extract_playlist_urls(html)

        categorized = {cat: [] for cat in CATEGORY_ORDER}
        all_channels = []

        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_playlist = {
                executor.submit(process_single_playlist, url, name): (url, name)
                for url, name in urls_with_names
            }

            for future in as_completed(future_to_playlist):
                try:
                    category, url, display_name, parsed_channels = future.result()
                    categorized[category].append((url, display_name, parsed_channels))
                    all_channels.extend(parsed_channels)
                except Exception as e:
                    url, name = future_to_playlist[future]
                    print(f"  Error processing {url}: {e}")

        generate_master_m3u(categorized)
        save_channel_index(all_channels)

        # 2. Generate EPG
        if CONFIG_FILE.exists():
            config = load_config()
            source = config.get("epg", {}).get("source", "iptvorg")

            channels = load_channels()
            if source == "epgshare":
                api_key = config.get("epg", {}).get("api_key", "")
                if api_key:
                    epg_root = fetch_epgshare(api_key, channels)
                    filtered_epg = filter_epg_by_channels(epg_root, channels)
                    write_epg(filtered_epg)
            elif source == "iptvorg":
                epg_root = fetch_iptvorg_epg(channels)
                filtered_epg = filter_epg_by_channels(epg_root, channels)
                write_epg(filtered_epg)
            elif source == "manual":
                url = config.get("epg", {}).get("xmltv_url", "")
                if url:
                    epg_root = fetch_manual_epg(url)
                    filtered_epg = filter_epg_by_channels(epg_root, channels)
                    write_epg(filtered_epg)

        load_stats()
        print(f"[{datetime.now()}] Refresh complete!")
        return {"status": "success"}
    except Exception as e:
        print(f"Refresh error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        refresh_in_progress = False


# ========== ROUTES ==========


@app.route("/")
def index():
    """Main dashboard."""
    load_stats()
    return render_template(
        "index.html",
        last_refresh=last_refresh,
        channel_count=channel_count,
        playlist_count=playlist_count,
        categories=CATEGORY_ORDER,
    )


@app.route("/playlist/master.m3u")
@app.route("/master.m3u")
def serve_master_m3u():
    """Serve the master M3U playlist (TiviMate compatible)."""
    if not MASTER_M3U.exists():
        refresh_playlists()
    return send_file(MASTER_M3U, mimetype="audio/x-mpegurl")


@app.route("/epg/epg.xml")
@app.route("/epg.xml")
def serve_epg():
    """Serve the EPG XML (TiviMate compatible)."""
    if not EPG_FILE.exists():
        refresh_playlists()
    return send_file(EPG_FILE, mimetype="application/xml")


@app.route("/api/stats")
def api_stats():
    """API endpoint for stats."""
    load_stats()
    return jsonify(
        {
            "last_refresh": last_refresh.isoformat() if last_refresh else None,
            "channel_count": channel_count,
            "playlist_count": playlist_count,
            "refresh_in_progress": refresh_in_progress,
        }
    )


@app.route("/api/channels")
def api_channels():
    """API endpoint for channel list."""
    if not CHANNEL_LIST.exists():
        return jsonify([])

    with open(CHANNEL_LIST) as f:
        channels = json.load(f)

    # Filter by search query
    query = request.args.get("q", "").lower()
    if query:
        channels = [ch for ch in channels if query in ch["name"].lower()]

    # Filter by category
    category = request.args.get("category")
    if category:
        # Load master M3U to get category info
        if MASTER_M3U.exists():
            with open(MASTER_M3U) as f:
                content = f.read()
            # Parse categories from M3U comments
            # For now, just return all
            pass

    return jsonify(channels[:100])  # Limit to 100 for performance


@app.route("/api/playlists")
def api_playlists():
    """API endpoint for playlist categories."""
    if not MASTER_M3U.exists():
        return jsonify({})

    with open(MASTER_M3U) as f:
        content = f.read()

    # Parse playlist info from comments
    playlists = {}
    current_category = None
    current_playlist = None

    for line in content.split("\n"):
        if line.startswith("# --- ") and line.endswith(" ---"):
            current_category = line[6:-4].strip()
            playlists[current_category] = []
        elif line.startswith("# Playlist: "):
            name = line[13:].strip()
            current_playlist = {"name": name, "channels": 0}
        elif line.startswith("# Channels: ") and current_playlist:
            current_playlist["channels"] = int(line[13:].strip())
            if current_category:
                playlists[current_category].append(current_playlist)
            current_playlist = None

    return jsonify(playlists)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Trigger a refresh of playlists and EPG."""
    if refresh_in_progress:
        return jsonify({"status": "already_running"})

    # Run refresh in background thread
    thread = threading.Thread(target=refresh_playlists)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started"})


@app.route("/copy-url/<path:url_type>")
def copy_url(url_type):
    """Return a copyable URL for TiviMate."""
    base_url = request.host_url.rstrip("/")

    if url_type == "m3u":
        return jsonify({"url": f"{base_url}/playlist/master.m3u"})
    elif url_type == "epg":
        return jsonify({"url": f"{base_url}/epg/epg.xml"})
    else:
        return jsonify({"error": "Invalid URL type"}), 400


# ========== SETUP ==========


def setup_app():
    """Initial setup."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    load_stats()

    # Generate initial files if they don't exist
    if not MASTER_M3U.exists():
        print("Initial playlist generation...")
        refresh_playlists()
    elif not EPG_FILE.exists():
        print("Initial EPG generation...")
        config = load_config()
        source = config.get("epg", {}).get("source", "iptvorg")
        channels = load_channels()

        if source == "epgshare":
            api_key = config.get("epg", {}).get("api_key", "")
            if api_key:
                epg_root = fetch_epgshare(api_key, channels)
                filtered_epg = filter_epg_by_channels(epg_root, channels)
                write_epg(filtered_epg)
        elif source == "iptvorg":
            epg_root = fetch_iptvorg_epg(channels)
            filtered_epg = filter_epg_by_channels(epg_root, channels)
            write_epg(filtered_epg)
        elif source == "manual":
            url = config.get("epg", {}).get("xmltv_url", "")
            if url:
                epg_root = fetch_manual_epg(url)
                filtered_epg = filter_epg_by_channels(epg_root, channels)
                write_epg(filtered_epg)


def start_scheduler():
    """Start the background scheduler for auto-refresh."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        refresh_playlists,
        "interval",
        hours=int(os.environ.get("REFRESH_INTERVAL_HOURS", "6")),
        id="playlist_refresh",
    )
    scheduler.start()
    print(
        f"Auto-refresh scheduled every {os.environ.get('REFRESH_INTERVAL_HOURS', '6')} hours"
    )


if __name__ == "__main__":
    setup_app()
    start_scheduler()

    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print(f"\n{'='*60}")
    print(f"Apsattv IPTV Web App")
    print(f"{'='*60}")
    print(f"Dashboard:  http://localhost:{port}")
    print(f"M3U URL:    http://localhost:{port}/playlist/master.m3u")
    print(f"EPG URL:    http://localhost:{port}/epg/epg.xml")
    print(f"{'='*60}\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
