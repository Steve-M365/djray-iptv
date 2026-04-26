# ✅ Deployment Complete: Apsattv IPTV on Raspberry Pi

## 🎉 Successfully Deployed!

Your IPTV aggregator is now **live** on your Raspberry Pi 4 at `192.168.1.142`.

---

## 🌐 Access URLs (Use in any IPTV player)

```
M3U Playlist: http://192.168.1.142:8090/master.m3u
EPG (Guide):  http://192.168.1.142:8090/epg.xml
Web Interface: http://192.168.1.142:8090/
```

**Test now:**
```bash
# From your Mac or any device on the same network:
open http://192.168.1.142:8090/master.m3u
# Should download/open the M3U file
```

---

## 📊 What's Running

| Item | Value |
|------|-------|
| **Device** | Raspberry Pi 4 (pi4) |
| **IP** | 192.168.1.142 |
| **Port** | 8090 |
| **Service** | Python HTTP Server (systemd) |
| **Status** | Active & enabled (auto-start on boot) |
| **Channels** | 6,781 unique across 8 categories |
| **M3U size** | 3.5 MB |
| **EPG size** | 1.1 MB |

**Categories in M3U:**
1. Australian (3 playlists)
2. Brazilian (4 playlists)
3. Content/Services (7 playlists)
4. LG Regional (31 playlists)
5. Main Playlists (5 playlists)
6. Platform/Device (8 playlists)
7. **Samsung Regional (17 playlists)** ← Fixed categorization
8. Specialized (8 playlists)
9. Other/Misc (remaining)

---

## 🔧 Management on Pi

All commands run on Pi via SSH (`ssh a-steve@192.168.1.142`):

```bash
# Check status
sudo systemctl status iptv-server

# Restart if needed
sudo systemctl restart iptv-server

# Stop
sudo systemctl stop iptv-server

# Disable autostart
sudo systemctl disable iptv-server

# View logs
sudo journalctl -u iptv-server -f
```

---

## 🔄 Updating the Playlist

Your Mac has the generator scripts. To update the Pi:

### Option A: One-command update (recommended)
```bash
cd /Users/steve/scripts/apsattv-iptv
./update-pi.sh
```
This regenerates master.m3u and epg.xml, then copies to Pi automatically.

### Option B: Manual copy
```bash
# On Mac, after regenerating:
scp /Users/steve/scripts/apsattv-iptv/output/master.m3u a-steve@192.168.1.142:~/iptv/
scp /Users/steve/scripts/apsattv-iptv/output/epg.xml a-steve@192.168.1.142:~/iptv/
```
No restart needed — Python HTTP server serves files live.

### Option C: Run generator on Pi (requires Python packages)
```bash
ssh a-steve@192.168.1.142
cd /home/a-steve/apsattv-iptv  # if you copy the whole folder
python3 main.py
python3 epg_generator.py
```

---

## 📱 Adding to IPTV Players

Use these URLs in any player on your home network:

| Player | How to Add |
|--------|------------|
| **VLC** | Media → Open Network Stream → Paste M3U URL |
| **Kodi** | TV → Add channels → Enter M3U → Settings → TV → EPG → Set XMLTV URL |
| **OTT Navigator** | Playlists → + → Add M3U URL |
| **Smart IPTV app** | Enter URL in app settings |
| **IPTV Smarters Pro** | Add playlist → Enter URL |

---

## 📁 Files on Pi

```
/home/a-steve/iptv/
├── master.m3u     (3.5 MB) — main playlist
├── epg.xml        (1.1 MB) — TV guide data
├── index.html     (8.5 KB) — landing page
├── README.md      — full documentation (see below)
└── update.sh      — update script

/etc/systemd/system/iptv-server.service  ← systemd unit
```

---

## 📖 Full Documentation

On the Pi: `cat /home/a-steve/iptv/README.md`  
Or on Mac: `open apsattv-iptv/PI-README.md`

Covers: troubleshooting, automation, external access, security.

---

## 🔍 Verify It's Working

```bash
# 1. Check Pi can serve files locally
ssh a-steve@192.168.1.142 "curl -s http://localhost:8090/master.m3u | head -5"

# 2. Check from Mac
curl -s http://192.168.1.142:8090/master.m3u | head -5

# 3. Count channels
curl -s http://192.168.1.142:8090/master.m3u | grep -c "^#EXTINF:-1"

# 4. Verify EPG
curl -s http://192.168.1.142:8090/epg.xml | head -5
```

---

## ⚙️ Service Details

- **Process:** `python3 -m http.server 8090`
- **User:** `a-steve` (non-root)
- **Working dir:** `/home/a-steve/iptv`
- **Started:** Auto on boot (systemd enabled)
- **Restart:** Auto on failure
- **Port:** 8090 (chosen to avoid Docker conflict on 8080)

---

## ⚠️ Important Notes

1. **Geo-restrictions:** Some channels may require VPN depending on your location
2. **EPG coverage:** Only ~100 channels from free source. For full guide, get EPGshare API key and regenerate
3. **Source updates:** apsattv.com updates playlists frequently — regenerate monthly
4. **Personal use only:** Respect content provider terms
5. **Local network:** Currently only accessible on your home network (192.168.1.x)

---

## 🚀 Next Steps

1. ✅ **Done:** Playlist deployed to Pi
2. **Now:** Add `http://192.168.1.142:8090/master.m3u` to your IPTV player
3. **Optional:** Set up daily auto-update (see PI-README.md)
4. **Optional:** Improve EPG coverage with EPGshare API key
5. **Optional:** Enable external access via port forwarding + DDNS (read PI-README.md)

---

## 📞 Quick Reference

| Action | Command |
|--------|---------|
| SSH to Pi | `ssh a-steve@192.168.1.142` |
| Check service | `sudo systemctl status iptv-server` |
| Restart service | `sudo systemctl restart iptv-server` |
| Update from Mac | `./update-pi.sh` (in apsattv-iptv folder) |
| View logs | `sudo journalctl -u iptv-server -f` |
| Stop service | `sudo systemctl stop iptv-server` |

---

## 🎯 Test Your Setup NOW

```bash
# On any device connected to your home WiFi:
open http://192.168.1.142:8090/
# Should show a nice landing page with stats

# Test M3U directly:
curl http://192.168.1.142:8090/master.m3u | head -20

# Test EPG:
curl http://192.168.1.142:8090/epg.xml | head -5
```

If all work → **You're all set!** 🎉

---

*Deployed: April 14, 2026 | Pi Model: 4 | OS: Debian 12 (bookworm)*  
*Source: https://apsattv.com/streams.html | Channels: 6,781 | Categories: 8*
