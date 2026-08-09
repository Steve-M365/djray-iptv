# DJRay IPTV — Test Plan

**Version:** 1.0  
**Date:** 2026-08-09  
**Total Channels:** 28,380  
**Total Sources:** 42  

---

## 1. GitHub Raw URL Tests

| # | Test | URL | Expected |
|---|------|-----|----------|
| 1.1 | Master M3U fetch | `https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/master.m3u` | 200 OK, valid M3U, ~28K channels |
| 1.2 | EPG fetch | `https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/epg.xml.gz` | 200 OK, valid gzip |
| 1.3 | Per-source M3U | `https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/sources/dearbulut.m3u` | 200 OK, valid M3U |
| 1.4 | TiviMate URL | `https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/sources/daddylive.m3u` | 200 OK |

**Commands:**
```bash
curl -sI "https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/master.m3u" | head -1
curl -sI "https://raw.githubusercontent.com/Steve-M365/djray-iptv/master/output/epg.xml.gz" | head -1
```

---

## 2. Normalizer Tests

| # | Test | Expected |
|---|------|----------|
| 2.1 | Run `python3 normalize_m3u_v2.py` | 42 sources, 28,380 channels |
| 2.2 | No duplicate URLs in master.m3u | `sort -u` count = total count |
| 2.3 | Group format is `Source | Country | Type` | Regex match |
| 2.4 | All source files exist in `output/sources/` | 42 files |
| 2.5 | dearbulut channels present | `grep -c 'dearbulut' output/master.m3u` > 0 |
| 2.6 | Country detection for dearbulut | `grep 'dearbulut' output/sources/dearbulut.m3u` shows country names |
| 2.7 | No empty channel names | `grep -c 'group-title="[^"]*|[^|]*|[^"]*",$' output/master.m3u` = 0 |

**Commands:**
```bash
python3 normalize_m3u_v2.py
grep -c '#EXTINF' output/master.m3u
grep -o 'group-title="[^"]*"' output/master.m3u | sort -u | wc -l
ls output/sources/ | wc -l
```

---

## 3. Flask App Tests

| # | Test | Expected |
|---|------|----------|
| 3.1 | `python3 app.py` starts | `http://localhost:5000` loads |
| 3.2 | Playlist picker shows all sources | Checkbox list with 42+ sources |
| 3.3 | Preset buttons work | Click "DaddyLive" → selects DaddyLive |
| 3.4 | Copy URL works | Clipboard contains GitHub raw URL |
| 3.5 | TiviMate URL format | `http://localhost:5000/tivi?daddylive` returns M3U |
| 3.6 | Custom selection | Select multiple sources → combined M3U |

**Commands:**
```bash
python3 app.py &
curl -s http://localhost:5000 | grep -c 'checkbox'
curl -s http://localhost:5000/tivi?daddylive | head -5
```

---

## 4. EPG Tests

| # | Test | Expected |
|---|------|----------|
| 4.1 | EPG file exists | `ls -la output/epg.xml.gz` |
| 4.2 | EPG is valid gzip | `file output/epg.xml.gz` shows gzip |
| 4.3 | EPG contains channel data | `zcat output/epg.xml.gz | grep -c '<channel'` > 0 |
| 4.4 | EPG channel count | `zcat output/epg.xml.gz | grep -c '<channel'` ~5,000+ |

**Commands:**
```bash
file output/epg.xml.gz
zcat output/epg.xml.gz | grep -c '<channel'
zcat output/epg.xml.gz | grep -c '<programme'
```

---

## 5. Data Integrity Tests

| # | Test | Expected |
|---|------|----------|
| 5.1 | No broken URLs | `grep -E '^https?://' output/master.m3u | wc -l` = channel count |
| 5.2 | No empty lines between EXTINF and URL | `awk '/^#EXTINF/{if(next!="") print NR}' output/master.m3u` = 0 |
| 5.3 | M3U header present | First line = `#EXTM3U` |
| 5.4 | Channel count matches | `grep -c '#EXTINF' output/master.m3u` = stated count |
| 5.5 | No duplicate channel names per group | `sort | uniq -d` = 0 |

---

## 6. Source Coverage Tests

| # | Source | Channels | Countries | Status |
|---|--------|----------|-----------|--------|
| 6.1 | dearbulut | 9,637 | 163 | ☐ |
| 6.2 | Vortexo | 4,264 | 1 | ☐ |
| 6.3 | apsattv | 4,065 | 31 | ☐ |
| 6.4 | LG Channels | 1,268 | 29 | ☐ |
| 6.5 | TCL TV | 1,129 | 3 | ☐ |
| 6.6 | DaddyLive | 1,020 | 1 | ☐ |
| 6.7 | Vidaa | 788 | 1 | ☐ |
| 6.8 | Samsung TV Plus | 717 | 16 | ☐ |
| 6.9 | Roku | 646 | 1 | ☐ |
| 6.10 | WhaleTV | 491 | 2 | ☐ |
| 6.11 | LocalNow | 447 | 1 | ☐ |
| 6.12 | Vizio | 429 | 1 | ☐ |
| 6.13 | Xumo | 387 | 1 | ☐ |
| 6.14 | Rakuten TV | 304 | 3 | ☐ |
| 6.15 | RedeiTV | 268 | 1 | ☐ |
| 6.16 | Xiaomi | 249 | 1 | ☐ |
| 6.17 | MetaX | 232 | 1 | ☐ |
| 6.18 | Orka TV | 195 | 1 | ☐ |
| 6.19 | Tubi | 179 | 1 | ☐ |
| 6.20 | Tablo | 164 | 1 | ☐ |
| 6.21 | MovieArk | 146 | 1 | ☐ |
| 6.22 | HP TV+ | 134 | 1 | ☐ |
| 6.23 | FreeLiveSports | 125 | 1 | ☐ |
| 6.24 | SportsTV | 124 | 1 | ☐ |
| 6.25 | SoulTV | 121 | 1 | ☐ |
| 6.26 | Rewarded.tv | 89 | 1 | ☐ |
| 6.27 | FreeTV | 84 | 1 | ☐ |
| 6.28 | iptv-org Sports | 84 | 1 | ☐ |
| 6.29 | Kogan TV+ | 82 | 1 | ☐ |
| 6.30 | KlowdTV | 78 | 1 | ☐ |
| 6.31 | iptv-org Australia | 75 | 1 | ☐ |
| 6.32 | Amazon Fire TV | 57 | 1 | ☐ |
| 6.33 | 10FAST | 55 | 1 | ☐ |
| 6.34 | Galaxy TV | 49 | 1 | ☐ |
| 6.35 | Zeasn | 45 | 1 | ☐ |
| 6.36 | 9FAST | 30 | 1 | ☐ |
| 6.37 | Cineverse | 29 | 1 | ☐ |
| 6.38 | OlhosnaTV | 29 | 1 | ☐ |
| 6.39 | IGOCast | 25 | 1 | ☐ |
| 6.40 | Fetch TV | 17 | 1 | ☐ |
| 6.41 | FreeMoviesPlus | 16 | 1 | ☐ |
| 6.42 | Veely | 7 | 1 | ☐ |

---

## 7. FastChannels Docker Tests

| # | Test | Expected |
|---|------|----------|
| 7.1 | `docker pull ghcr.io/kineticman/fastchannels:latest` | Image pulled |
| 7.2 | `docker run -d --name fastchannels -p 5523:5523 ghcr.io/kineticman/fastchannels:latest` | Container running |
| 7.3 | `curl http://localhost:5523` | Web UI loads |
| 7.4 | Channel list available | API returns channels |

---

## 8. TiviMate Integration Tests

| # | Test | Expected |
|---|------|----------|
| 8.1 | Add M3U URL in TiviMate | Channels load |
| 8.2 | EPG URL works | Programme data displays |
| 8.3 | Groups display correctly | Source \| Country \| Type hierarchy |
| 8.4 | Channel logos load | tvg-logo URLs resolve |
| 8.5 | Stream playback | Channels play without buffering |

---

## 9. Performance Tests

| # | Test | Expected |
|---|------|----------|
| 9.1 | M3U file size | < 50MB |
| 9.2 | Normalizer run time | < 30 seconds |
| 9.3 | Flask app response time | < 2 seconds |
| 9.4 | GitHub raw URL latency | < 5 seconds |

---

## 10. Regression Tests

| # | Test | Expected |
|---|------|----------|
| 10.1 | Existing sources still work | All 41 original sources present |
| 10.2 | No channels lost | 28,380 ≥ 19,942 (previous) |
| 10.3 | Group hierarchy maintained | All groups follow `Source \| Country \| Type` |
| 10.4 | EPG still merges correctly | `epg.xml.gz` valid |

---

## Sign-Off

| Tester | Date | Status |
|--------|------|--------|
| | | ☐ PASS / ☐ FAIL |
