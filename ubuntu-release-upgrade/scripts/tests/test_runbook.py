from ubuntu_release_upgrade import runbook


def _mock_path():
    return {
        "flavor": "kubuntu",
        "prompt_policy": "lts",
        "meta_file": "meta-release-lts",
        "from": {"codename": "alpha", "version": "1.0", "name": "Alpha"},
        "to": {"codename": "beta", "version": "2.0", "name": "Beta"},
        "path_open": True,
        "development_only": False,
        "current_release_found": True,
        "interim_alternative": None,
        "advice": "Path is OPEN.",
    }


def _mock_repos():
    return {"current_codename": "alpha", "target_codename": "beta", "entries": [], "warnings": []}


def _patch(monkeypatch, desktop="other"):
    monkeypatch.setattr(runbook.release, "check_path", lambda target=None: _mock_path())
    monkeypatch.setattr(runbook.repos, "inventory", lambda *a, **k: _mock_repos())
    monkeypatch.setattr(runbook.system, "detect_desktop", lambda: desktop)


def test_generate_creates_runbook(tmp_path, monkeypatch):
    _patch(monkeypatch)
    out = tmp_path / "rb.md"
    result = runbook.generate(out=str(out))
    assert result["status"] == "created"
    text = out.read_text()
    assert "alpha -> beta" in text
    assert "## Phase 0" in text
    assert "## Phase 5" in text


def test_generate_no_clobber(tmp_path, monkeypatch):
    _patch(monkeypatch)
    out = tmp_path / "rb.md"
    out.write_text("EXISTING PROGRESS")
    result = runbook.generate(out=str(out))
    assert result["status"] == "exists"
    assert out.read_text() == "EXISTING PROGRESS"


def test_generate_force_overwrites(tmp_path, monkeypatch):
    _patch(monkeypatch)
    out = tmp_path / "rb.md"
    out.write_text("EXISTING PROGRESS")
    result = runbook.generate(out=str(out), force=True)
    assert result["status"] == "created"
    assert "EXISTING PROGRESS" not in out.read_text()


def test_kde_section_gated_on_desktop(tmp_path, monkeypatch):
    _patch(monkeypatch, desktop="kde")
    out = tmp_path / "rb.md"
    runbook.generate(out=str(out), force=True)
    assert "KDE:" in out.read_text()

    _patch(monkeypatch, desktop="gnome")
    out2 = tmp_path / "rb2.md"
    runbook.generate(out=str(out2), force=True)
    assert "KDE:" not in out2.read_text()
