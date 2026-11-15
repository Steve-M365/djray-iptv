import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import epg  # noqa: E402
from playlist import Channel  # noqa: E402


def chan(name, tvg_id="", country="Australia", url=None):
    return Channel(
        name=name,
        url=url or f"https://example.com/{name.lower().replace(' ', '-')}.m3u8",
        source="Src",
        source_id="src",
        tvg_id=tvg_id,
        country=country,
    )


def test_core_id_strips_service_prefix_suffix_and_plex_hash():
    assert epg._core_id("samsungtvplus-ATBD3700001EH") == "atbd3700001eh"
    assert epg._core_id("plutotv-673247127d5da5000817b4d6") == "673247127d5da5000817b4d6"
    suffix = "63504925a97bd70eaef54f01"
    assert epg._core_id(f"plex-697140a85d851f5e69414688-{suffix}") == suffix
    assert epg._core_id("ABCPerth.au") == "abcperth"


def test_service_detection():
    assert epg._service_of("samsungtvplus-abc") == "samsungtvplus"
    assert epg._service_of("ABCPerth.au") == ""


def test_matcher_links_epg_id_to_same_service_channel():
    channels = [chan("X-Mas Mix", tvg_id="samsungtvplus-atbd3700001eh", country="Germany")]
    matcher = epg.Matcher(channels)
    hits = matcher.match("ATBD3700001EH", ["X-Mas Mix"], [], allow_names=False)
    assert hits == channels


def test_matcher_does_not_cross_services():
    channels = [chan("Thing", tvg_id="plutotv-abc123")]
    matcher = epg.Matcher(channels)
    hits = matcher.match("samsungtvplus-abc123", [], [], allow_names=False)
    assert hits == []


def test_matcher_name_match_respects_country():
    channels = [chan("Sky News", country="Australia")]
    matcher = epg.Matcher(channels)
    assert matcher.match("sky.au", ["Sky News"], ["Australia"]) == channels
    assert matcher.match("sky.us", ["Sky News"], ["United States"]) == []


def test_normalise_strips_quality_and_country_suffix():
    assert epg.normalise("ABC News (Australia)") == "abc news"
    assert epg.normalise("Sky News HD") == "sky news"
    assert epg.normalise("Sky News TV") == "sky news"
    assert epg.normalise("AU: Fox Sports") == "fox sports"