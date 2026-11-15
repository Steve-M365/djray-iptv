import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import playlist as pl  # noqa: E402


def chan(**kw):
    base = dict(name="Test Channel", url="https://example.com/a.m3u8", source="Src", source_id="src")
    base.update(kw)
    return pl.Channel(**base)


def test_parser_keeps_player_options_and_comma_names():
    text = """#EXTM3U
#EXTINF:-1 tvg-id="abc.au" tvg-name="ABC, Sydney" group-title="Old",ABC Sydney
#EXTVLCOPT:http-user-agent=Example/1.0
https://example.com/abc.m3u8
"""
    channels = pl.parse_playlist(text, "src", "Src", "Australia")
    assert len(channels) == 1
    ch = channels[0]
    assert ch.name == "ABC Sydney"
    assert ch.tvg_name == "ABC, Sydney"
    assert ch.tvg_id == "abc.au"
    assert any("EXTVLCOPT" in e for e in ch.extras)
    assert ch.url == "https://example.com/abc.m3u8"


def test_parser_skips_entries_without_url():
    text = "#EXTM3U\n#EXTINF:-1,Orphan\n#EXTINF:-1,Real\nhttps://example.com/real.m3u8\n"
    channels = pl.parse_playlist(text, "src", "Src")
    assert [c.name for c in channels] == ["Real"]


def test_normalise_drops_template_and_non_http_urls():
    channels = [
        chan(url="https://ads.example.com/x.m3u8?app=[APP_NAME]"),
        chan(url="rtmp://example.com/live"),
        chan(url="https://example.com/ok.m3u8", name="Good"),
    ]
    out = pl.normalise(channels)
    assert [c.name for c in out] == ["Good"]


def test_normalise_deduplicates_urls():
    channels = [
        chan(url="https://example.com/same.m3u8", name="One"),
        chan(url="https://example.com/same.m3u8", name="Two"),
    ]
    out = pl.normalise(channels)
    assert len(out) == 1


def test_country_hint_beats_source_default():
    ch = chan(default_country="United States", group_hint="Vortexo | Australia | Entertainment")
    assert pl.infer_country(ch) == "Australia"


def test_flat_group_names():
    ch = chan(country="Australia", ctype="Sports")
    assert pl.group_country(ch) == "Australia | Sports"
    assert "|" in pl.group_country(ch)
    assert "|" not in pl.group_type(ch)


def test_write_playlist_groups_and_order(tmp_path: Path):
    channels = [
        chan(name="Zed", country="Australia", ctype="Sports"),
        chan(name="Alpha", country="Australia", ctype="Sports", url="https://example.com/2.m3u8"),
        chan(name="News", country="United States", ctype="News", url="https://example.com/3.m3u8"),
    ]
    target = tmp_path / "master.m3u"
    count = pl.write_playlist(channels, target, title="Test", grouping="country")
    text = target.read_text()
    assert count == 3
    assert text.startswith("#EXTM3U")
    assert text.index("Australia | Sports") < text.index("United States | News")
    # channels sorted alphabetically inside a group
    assert text.index("Alpha") < text.index("Zed")


def test_preset_matches_afl_and_f1():
    channels = [
        chan(name="7AFL", url="https://example.com/1.m3u8"),
        chan(name="Fox Footy", url="https://example.com/2.m3u8"),
        chan(name="Formula 1 Live", url="https://example.com/3.m3u8"),
        chan(name="Cooking", url="https://example.com/4.m3u8"),
    ]
    afl = pl.build_preset("afl", pl.PRESETS["afl"], channels)
    f1 = pl.build_preset("f1", pl.PRESETS["f1"], channels)
    assert {c.name for c in afl} == {"7AFL", "Fox Footy"}
    assert {c.name for c in f1} == {"Formula 1 Live"}


def test_dedupe_named_prefers_epg_match():
    a = chan(name="Sky News", country="Australia", url="https://example.com/a.m3u8")
    b = chan(name="Sky News", country="Australia", url="https://example.com/b.m3u8", epg_matched=True)
    out = pl.dedupe_named([a, b])
    assert len(out) == 1
    assert out[0].epg_matched is True