# 🍓 DJRay IPTV on Raspberry Pi

**Host:** pi4 (192.168.1.142)  
**Service:** Python HTTP server on port 8090  
**Status:** Running as systemd service

---

## 📺 Access URLs

**From any device on your local network:**

```
M3U Playlist: http://192.168.1.142:8090/master.m3u
EPG (XMLTV):  http://192.168.1.142:8090/epg.xml
Web UI:       http://192.168.1.142:8090/
```

**On the Pi itself:**
```bash
curl http://localhost:8090/master.m3u
```

---

## 🎯 What's Included

- **master.m3u** — Complete playlist with 6,781 unique channels across 8 categories
- **epg.xml** — Electronic Program Guide (~100 channels from free sources)
- **index.html** — Nice landing page showing stats and URLs

---

## 🔧 Management

### Check Service Status
```bash
sudo systemctl status iptv-server
```

### Restart Service
```bash
sudo systemctl restart iptv-server
```

### Stop Service
```bash
sudo systemctl stop iptv-server
```

### Disable Auto-Start
```bash
sudo systemctl disable iptv-server
```

### View Logs
```bash
sudo journalctl -u iptv-server -f
```

---

## 🔄 Updating Playlists

Playlist data is generated on your Mac and copied to the Pi.

### From Mac (after regenerating)
```bash
scp /Users/steve/scripts/djray-iptv/output/master.m3u a-steve@192.168.1.142:~/iptv/
scp /Users/steve/scripts/djray-iptv/output/epg.xml a-steve@192.168.1.142:~/iptv/
```
Files are served automatically (no restart needed).

### On Pi (if generator installed there)
```bash
cd /home/a-steve/djray-iptv
python3 main.py
python3 epg_generator.py
# Files automatically appear in ~/iptv/
```

---

## 📡 Using the Playlist

Add these URLs to any IPTV player on your network:

**VLC (Desktop):**  
Media → Open Network Stream → `http://192.168.1.142:8090/master.m3u`

**Kodi:**  
TV → Guide → Add channel → Enter M3U URL  
Settings → TV → EPG → XMLTV URL: `http://192.168.1.142:8090/epg.xml`

**OTT Navigator (Android):**  
Add playlist → New → Enter URL

**Smart TVs:**  
Use IPTV player app (Smart IPTV, SET IPTV, etc.) → Enter playlist URL

---

## 🔍 Troubleshooting

**"Cannot connect to 192.168.1.142:8090"**
1. Check Pi is on: `ping 192.168.1.142`
2. Check service: `sudo systemctl status iptv-server`
3. Check port: `sudo ss -tulpn | grep 8090`
4. Restart: `sudo systemctl restart iptv-server`

**"Page loads but blank/404"**
```bash
ls -la /home/a-steve/iptv/
# Should show: master.m3u, epg.xml, index.html
```

**"EPG not showing in player"**
- EPG from free source covers only ~100 channels
- For better coverage, configure EPGshare on source machine
- Regenerate epg.xml and copy to Pi

**"Some channels not working"**
- Source playlists may have expired links
- Regenerate master.m3u from source
- Some channels are geo-blocked; use VPN if needed

---

## 🛠️ Technical Details

- **Web Server:** Python 3 `http.server` (built-in)
- **Port:** 8090 (avoids conflict with Docker on 8080)
- **User:** a-steve (non-root)
- **Auto-start:** Enabled (systemd)
- **Restart policy:** Automatic on failure
- **Working directory:** `/home/a-steve/iptv`
- **Systemd unit:** `/etc/systemd/system/iptv-server.service`

---

## 🌐 External Access (Optional)

To access from outside your home network:

1. **Port forward** on router: forward port 8090 → 192.168.1.142:8090
2. **Dynamic DNS** (if no static IP): DuckDNS, No-IP, etc.
3. **Security:** Consider VPN instead of direct exposure

---

## 🔄 Automation (Optional)

### Daily update on Pi
```bash
crontab -e
# Add:
0 3 * * * /home/a-steve/iptv/update.sh >> /home/a-steve/iptv/update.log 2>&1
```

### Or update from Mac automatically
Add to Mac crontab:
```bash
0 3 * * * scp /Users/steve/scripts/djray-iptv/output/*.m3u a-steve@192.168.1.142:~/iptv/ && scp /Users/steve/scripts/djray-iptv/output/epg.xml a-steve@192.168.1.142:~/iptv/
```

---

## 📊 Statistics

- **Total channels:** 6,781 unique
- **M3U entries:** 8,818
- **Categories:** 8
- **Source playlists:** 75+
- **EPG programs:** ~5,600

---

## 📝 Notes

- Source: https://apsattv.com/streams.html
- Personal use only
- Some channels geo-restricted
- EPG limited with free source
- Service survives reboot

---

## 🎉 Quick Test

From any computer on your network:
```bash
# Test M3U
curl http://192.168.1.142:8090/master.m3u | head -5

# Test EPG
curl http://192.168.1.142:8090/epg.xml | head -5

# Open in browser
open http://192.168.1.142:8090/
```

If all work → add URLs to your IPTV player!

---

*Raspberry Pi 4 — Debian 12 — Python HTTP Server*
