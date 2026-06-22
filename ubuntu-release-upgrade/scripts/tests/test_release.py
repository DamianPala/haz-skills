from ubuntu_release_upgrade import release


def test_interim_alternative_none_under_normal_policy():
    assert release._interim_alternative("normal", "noble", None) is None


def test_interim_alternative_none_when_next_is_the_lts(monkeypatch):
    lts_target = {"Dist": "resolute", "Version": "26.04 LTS"}
    monkeypatch.setattr(release, "_next_under_normal", lambda _: lts_target)
    # On an interim, the next release under normal IS the upcoming LTS: nothing skipped.
    assert release._interim_alternative("lts", "questing", lts_target) is None


def test_interim_alternative_surfaces_skipped_interim(monkeypatch):
    interim = {"Dist": "sunny", "Version": "26.10", "Supported": "1"}
    monkeypatch.setattr(release, "_next_under_normal", lambda _: interim)
    lts_target = {"Dist": "future-lts", "Version": "28.04 LTS"}
    result = release._interim_alternative("lts", "resolute", lts_target)
    assert result == {"codename": "sunny", "version": "26.10", "path_open": True}


def test_select_target_version_match_is_anchored():
    dists = [
        {"Dist": "noble", "Version": "24.04 LTS"},
        {"Dist": "resolute", "Version": "26.04 LTS"},
    ]
    # version-number target matches the version's leading token
    assert release._select_target(dists, "noble", "26.04")[1]["Dist"] == "resolute"
    # codename target matches exactly
    assert release._select_target(dists, "noble", "resolute")[1]["Dist"] == "resolute"
    # a substring like "4.0" must NOT match "24.04"
    assert release._select_target(dists, "noble", "4.0")[1] is None


def test_parse_meta_blocks_and_version_ordering():
    text = (
        "Dist: noble\nVersion: 24.04 LTS\nSupported: 1\n\n"
        "Dist: resolute\nVersion: 26.04 LTS\nSupported: 0\n"
    )
    blocks = release._parse_meta(text)
    assert [b["Dist"] for b in blocks] == ["noble", "resolute"]
    assert release._version_of(blocks[1]) == 26.04
