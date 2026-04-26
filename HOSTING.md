# Hosting Your Apsattv Playlist

## ⚠️ Important Note About Google Sites

**Google Sites CANNOT host raw .m3u or .xml files for IPTV players.**

Google Sites only serves HTML web pages. M3U/XML files need direct URL access (e.g., `https://example.com/file.m3u`). Uploading to Google Sites or Google Drive does not provide a direct, publicly accessible URL that IPTV players can read.

**Workarounds that DO NOT work well:**
- Google Drive sharing links → require authentication
- Google Sites file embed → not direct URL
- Blogger/other Google services → same limitation

---

## ✅ Recommended: GitHub Pages (Free, Reliable)

GitHub Pages serves static files with direct URLs. Perfect for M3U/EPG.

### One-Time Setup

```bash
# 1. Create a GitHub account if you don't have one

# 2. Create new repository (public)
#    Visit: https://github.com/new
#    Repository name: apsattv-m3u (or any name)
#    Set to PUBLIC (required for Pages)

# 3. Push your files
cd apsattv-iptv
git init
git add .
git commit -m "Initial commit"

# Set your remote (replace USER with your GitHub username)
git remote add origin https://github.com/USER/apsattv-m3u.git
git branch -M main
git push -u origin main
```

### Enable GitHub Pages

1. Go to your repo: `https://github.com/USER/apsattv-m3u`
2. Click **Settings** → **Pages**
3. Under **Build and deployment**:
   - Source: `Deploy from a branch`
   - Branch: `main` → folder: `/ (root)`
4. Click **Save**

Your site will be live at:
```
https://USER.github.io/apsattv-m3u/
```

M3U URL: `https://USER.github.io/apsattv-m3u/master.m3u`  
EPG URL: `https://USER.github.io/apsattv-m3u/epg.xml`

**Wait 1-5 minutes** after enabling Pages. Refresh occasionally.

---

## 🔄 Updating Files

After making changes (rerunning the scripts):

```bash
cd apsattv-iptv
git add output/
git commit -m "Update $(date +%Y-%m-%d)"
git push
```

GitHub Pages auto-updates within minutes.

---

## Alternative Static Hosts

If you prefer other hosts, these also work with direct file URLs:

| Service | Free? | Notes |
|---------|-------|-------|
| **Netlify** | Yes | Drag & drop `output/` folder |
| **Vercel** | Yes | Similar to Netlify |
| **Cloudflare Pages** | Yes | Fast global CDN |
| **Firebase Hosting** | Free tier | Google-hosted |
| **AWS S3 Static Website** | 12 months free | Requires AWS account |

**All work the same way:** Upload `master.m3u` and `epg.xml` → get a direct URL.

---

## Testing Your URLs

Before sharing, test the URLs work:

```bash
# Test M3U is accessible
curl -I https://USER.github.io/apsattv-m3u/master.m3u
# Should return HTTP 200 and Content-Type: audio/x-mpegurl or text/plain

# Test EPG
curl -I https://USER.github.io/apsattv-m3u/epg.xml
# Should return HTTP 200 and Content-Type: application/xml
```

If you get 404:
- Wait a few minutes (GitHub Pages propagation)
- Check Pages is enabled and pointing to `main` branch root
- Ensure `master.m3u` and `epg.xml` are committed and pushed

---

## Using the Playlist

In your IPTV player (VLC, Kodi, IPTV Smarters, etc.):

**Playlist URL:** `https://USER.github.io/apsattv-m3u/master.m3u`  
**EPG URL:** `https://USER.github.io/apsattv-m3u/epg.xml`

### Player Setup Examples

**VLC:**
- Media → Open Network Stream → Paste M3U URL

**Kodi:**
- TV → TV guide → "Add channel" → Enter M3U URL
- Settings → TV → EPG → Set XMLTV URL to EPG URL

**OTT Navigator (Android):**
- Add playlist → "New playlist" → M3U URL

**Smart TVs** (Samsung/LG/Android TV):
- Use built-in IPTV apps or install third-party (Smart IPTV, SET IPTV, etc.)
- Enter the M3U URL in app settings

---

## Automation (Optional)

Set up daily auto-update (requires GitHub token with repo permissions):

```bash
# Add to crontab: crontab -e
0 2 * * * cd /path/to/apsattv-iptv && /usr/bin/python3 main.py && /usr/bin/python3 epg_generator.py && git add output/ && git commit -m "Auto-update $(date +\%Y-\%m-\%d)" && git push
```

Or use the included `deploy.py` script with GitHub CLI.

---

## Troubleshooting

**"File not found (404)"**
- GitHub Pages may take 2-5 minutes to go live after first push
- Check repo Settings → Pages → source is `main` branch root
- Verify files are in repo root (not in a subfolder)
- Visit `https://USER.github.io/apsattv-m3u/master.m3u` directly in browser

**"Playlist loads but no channels"**
- Open master.m3u in text editor to verify content
- Check console output of main.py for errors fetching playlists
- Some source playlists may be temporarily down (retry later)

**"EPG not showing"**
- EPG coverage from iptvorg is limited (~100 channels out of 6,781)
- For full coverage, edit config.json → use `"source": "epgshare"` and add your API key from https://epgshare.com
- After updating config, rerun `python epg_generator.py`

**"Google Sites only" constraint**
If you must use Google Sites as front-end:
1. Host your M3U/EPG on GitHub Pages (as above)
2. Create a Google Site with a link/button pointing to the GitHub Pages URL
3. Users click through to get the actual playlist URL
4. This satisfies "host on Google Sites" while technically hosting files elsewhere

---

## File Summary

| File | Size | Purpose |
|------|------|---------|
| `output/master.m3u` | ~3.5 MB | Complete playlist with categories |
| `output/epg.xml` | ~1.1 MB | XMLTV EPG data |
| `output/channels.json` | ~2.6 MB | Channel index (for reference) |
| `main.py` | - | M3U generator script |
| `epg_generator.py` | - | EPG generator script |
| `config.json` | - | Configuration (EPG source, cleanup rules) |
| `README.md` | - | Full documentation |

---

## Next Steps

1. Choose a hosting provider (GitHub Pages recommended)
2. Deploy `master.m3u` and `epg.xml`
3. Get your public URLs
4. Add the URLs to your IPTV player
5. Share with others (respect apsattv.com's terms)

Enjoy your aggregated IPTV service!
