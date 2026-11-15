# Legacy pipelines (archived)

Everything in this directory is **archived and unsupported**. It is kept for
reference only. The supported pipeline lives in the repository root and is
driven by `build.py` (see the top-level `README.md`).

## v1 (`legacy/v1/`)

The original apsattv-only aggregator:

- `main.py` – scraped `apsattv.com/streams.html` and concatenated every playlist
  into `output/master.m3u` with `--- Section ---` headers.
- `epg_generator.py` – placeholder/EPGshare guide generator.
- `normalize_m3u.py` – the first Source → Country → Type normalizer.
- `merge_epg.py`, `fetch_all.sh`, `build_master.sh`, `stats.py`,
  `analyze_channels.py`, `deploy.py`, `deploy.sh`, `update-pi.sh`,
  `build_afl.py`, `build_f1.py` – supporting scripts from the same era.

**Output isolation:** these scripts now write to `legacy/v1/output/`, never to
the production `output/` directory. That guarantees the "one writer per output
file" rule — only the current pipeline may write `output/master.m3u`,
`output/epg.xml.gz` and `output/channels.json`.

The scripts still reference the repository-root `config.json` and the
repository virtualenv. They are not part of CI and are not tested.

## docs (`legacy/docs/`)

Deployment and Raspberry Pi notes from the v1 era. Superseded by
`README.md` and `.github/workflows/rebuild.yml`.