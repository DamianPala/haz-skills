from ubuntu_release_upgrade import repos


def test_classify_entry():
    ppa = "https://ppa.launchpadcontent.net/x/y/ubuntu"
    assert repos._classify_entry(ppa, "questing", "questing") == "codename"
    assert repos._classify_entry("https://example.com", "stable", "questing") == "generic"
    assert repos._classify_entry("https://example.com", "noble", "questing") == "codename-other"
    assert repos._classify_entry("https://example.com", "v2.0", "questing") == "other"


def test_official_ubuntu_archive_is_excluded():
    assert repos._classify_entry("http://archive.ubuntu.com/ubuntu", "questing", "questing") == "official"
    assert repos._classify_entry("http://pl.archive.ubuntu.com/ubuntu", "questing", "questing") == "official"


def test_parse_list_enabled_commented_and_disabled(tmp_path):
    f = tmp_path / "vendor.list"
    f.write_text(
        "# a comment\n"
        "deb https://example.com/apt questing main\n"
        "# deb https://example.com/apt questing extra\n"
    )
    entries = repos._parse_list(str(f), "questing")
    assert len(entries) == 2
    enabled = [e for e in entries if e["enabled"]]
    assert len(enabled) == 1
    assert enabled[0]["suite"] == "questing"
    assert enabled[0]["kind"] == "codename"


def test_parse_list_disabled_file(tmp_path):
    f = tmp_path / "vendor.list.disabled"
    f.write_text("deb https://example.com/apt questing main\n")
    entries = repos._parse_list(str(f), "questing")
    assert entries[0]["enabled"] is False


def test_parse_sources_deb822_enabled_and_disabled(tmp_path):
    f = tmp_path / "vendor.sources"
    f.write_text(
        "Types: deb\n"
        "URIs: https://example.com/apt\n"
        "Suites: questing\n"
        "Components: main\n"
        "Enabled: no\n"
    )
    entries = repos._parse_sources(str(f), "questing")
    assert len(entries) == 1
    assert entries[0]["enabled"] is False
    assert entries[0]["suite"] == "questing"
    assert entries[0]["kind"] == "codename"
