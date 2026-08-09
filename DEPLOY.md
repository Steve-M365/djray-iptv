# 🚀 Quick Start: Deploy Your DJRay IPTV Service

You have generated:
- `output/master.m3u` — 3.5 MB playlist with **6,781 channels** across 8 categories
- `output/epg.xml` — 1.1 MB EPG (limited coverage from free sources)
- `output/channels.json` — channel index

## Step 1: Choose a Host (Free Options)

### ✅ GitHub Pages (Recommended)

**Pros:** Free, reliable, direct file URLs, no bandwidth limits  
**Cons:** Requires GitHub account, one-time setup

```bash
# Install GitHub CLI (optional, for easy deployment)
# Mac: brew install gh
# Windows: winget install --id GitHub.cli
# Linux: sudo apt install gh

# Authenticate
gh auth login

# Create and push repo
cd djray-iptv
git init
git add .
git commit -m "Deploy apsattv IPTV"
gh repo create apsattv-m3u --public --source=. --remote=origin --push
```

Then enable Pages:
1. Visit: https://github.com/YOUR_USERNAME/apsattv-m3u/settings/pages
2. Source: **Deploy from a branch** → Branch: `main` → Folder: `/ (root)`
3. Save

Your URLs will be:
```
M3U: https://YOUR_USERNAME.github.io/apsattv-m3u/master.m3u
EPG: https://YOUR_USERNAME.github.io/apsattv-m3u/epg.xml
```

---

### Netlify (Drag & Drop)

1. Go to https://app.netlify.com/drop
2. Drag the `output/` folder
3. Netlify gives you a URL like `https://your-site.netlify.app/`
4. Your playlist URL: `https://your-site.netlify.app/master.m3u`

---

### Vercel

```bash
npm i -g vercel
vercel --prod
# Point to output/ directory
```

---

## Step 2: Test Your URLs

After deploying, test in browser:
```
https://YOUR-SITE/master.m3u
```
Should download or display M3U text. If you see JSON or 404, deployment isn't done yet.

---

## Step 3: Add to IPTV Player

| Player | How to Add |
|--------|-----------|
| **VLC** | Media → Open Network Stream → Paste M3U URL |
| **Kodi** | TV → "Channels" → "Add channels" → Enter M3U URL → Guide → Set EPG URL |
| **OTT Navigator** | Playlists → + → "Add playlist" → Enter URL |
| **Smart IPTV (Samsung/LG)** | Upload via app.smarttvnordic.com or enter URL in app settings |
| **IPTV Smarters Pro** | Add playlist → Enter URL and EPG URL |

---

## Step 4: Handle EPG Coverage

Current EPG covers only ~100 channels from free sources. For full coverage:

### Option A: EPGshare (Free API, ~7-day schedule)
1. Sign up at https://epgshare.com
2. Get API key from dashboard
3. Edit `config.json`:
   ```json
   {
     "epg": {
       "source": "epgshare",
       "api_key": "YOUR_API_KEY"
     }
   }
   ```
4. Rerun: `python epg_generator.py`
5. Redeploy `epg.xml`

### Option B: Accept limited EPG (just channel names, no schedules)
Current state — players show "No program information" for most channels.

---

## Step 5: Automate Updates (Optional)

Source playlists change frequently. Set daily auto-update:

### Using Crontab (Linux/Mac)
```bash
crontab -e
# Add:
0 2 * * * cd /path/to/djray-iptv && /usr/bin/python3 main.py && /usr/bin/python3 epg_generator.py && git add output/ && git commit -m "Update $(date +\%Y-\%m-\%d)" && git push 2>&1 >> /tmp/iptv-update.log
```

### Using GitHub Actions (no server needed)
Create `.github/workflows/update.yml` in your repo:
```yaml
name: Daily Update
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - run: pip install -r requirements.txt
      - run: python main.py
      - run: python epg_generator.py
      - run: git config --global user.email "actions@github.com"
      - run: git config --global user.name "GitHub Action"
      - run: git add output/
      - run: git commit -m "Daily update $(date)"
      - run: git push
```

This auto-updates daily at 2 AM UTC.

---

## Troubleshooting

### ❌ "404 Not Found" on GitHub Pages
- Wait 2-5 minutes after enabling Pages
- Check: Settings → Pages → Source = `main` branch, root folder
- Confirm `master.m3u` is committed to root of repo (not in subfolder)
- Access directly: `https://username.github.io/repo-name/master.m3u`

### ❌ "Failed to load EPG" in player
- EPG XML may be malformed. Validate: https://www.xmlvalidation.com/
- Check `epg.xml` size (>0 bytes)
- Some players require specific XMLTV format; try another player

### ❌ "Some playlists returned no channels"
- apsattv.com playlists occasionally go down
- The script logs errors but continues; check `output/master.m3u` to see which sections are empty
- Re-run later — apsattv updates often

### ❌ "Google Sites requirement"
If you MUST use Google Sites (e.g. organization policy):
- Create Google Site
- Add a prominent link/button: "Download IPTV Playlist" → points to your GitHub Pages URL
- Explain that technical limitations prevent direct hosting on Google Sites
- This is the only practical workaround

---

## File Reference

```
djray-iptv/
├── main.py                  # M3U generator (parallel fetch, 75 sources)
├── epg_generator.py         # EPG generator (iptv-org or EPGshare)
├── config.json              # EPG source, channel cleanup rules
├── requirements.txt         # Python dependencies
├── setup.sh / setup.bat     # Quick environment setup
├── deploy.py                # Git deployment helper (requires gh CLI)
├── analyze_channels.py      # Statistics utility
├── README.md                # Technical documentation
├── HOSTING.md              # Detailed hosting guide (this file)
├── output/                  # Generated files (upload these)
│   ├── master.m3u           # ← Main playlist file
│   ├── epg.xml              # ← EPG file
│   └── channels.json        # Channel index (reference only)
└── AGENTS.md               # Repository operational guide (if you want to commit)
```

---

## Need Help?

- apsattv.com source playlists: https://apsattv.com/streams.html
- GitHub Pages docs: https://docs.github.com/en/pages
- EPGshare: https://epgshare.com
- IPTV player support: consult your player's documentation

---

**Ready?** Push `output/master.m3u` and `output/epg.xml` to your host and share the URL!
