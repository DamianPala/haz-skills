import hashlib

import pytest

from ubuntu_release_upgrade import conffile, system


def _write_pair(tmp_path, current: str, incoming: str):
    conf = tmp_path / "x.conf"
    conf.write_text(current)
    (tmp_path / "x.conf.dpkg-new").write_text(incoming)
    return conf


def test_missing_pending_change_raises(tmp_path):
    with pytest.raises(system.NotApplicableError):
        conffile.classify(str(tmp_path / "nope.conf"))


def test_not_user_modified_recommends_maintainer(tmp_path, monkeypatch):
    conf = _write_pair(tmp_path, "a=1\nb=2\n", "a=1\nb=3\n")
    current_md5 = hashlib.md5(conf.read_text().encode()).hexdigest()  # noqa: S324
    monkeypatch.setattr(conffile, "_stored_md5", lambda *_: current_md5)
    result = conffile.classify(str(conf))
    assert result["user_modified"] is False
    assert "(Y)" in result["recommendation"]


def test_user_modified_real_change_recommends_keep(tmp_path, monkeypatch):
    conf = _write_pair(tmp_path, "a=1\nb=user-edit\n", "a=1\nb=2\n")
    monkeypatch.setattr(conffile, "_stored_md5", lambda *_: "stored-differs")
    result = conffile.classify(str(conf))
    assert result["user_modified"] is True
    assert result["changes_comments_only"] is False
    assert "KEEP" in result["recommendation"]


def test_user_modified_comments_only_leans_take_new(tmp_path, monkeypatch):
    conf = _write_pair(tmp_path, "a=1\n", "a=1\n# maintainer note\n")
    monkeypatch.setattr(conffile, "_stored_md5", lambda *_: "stored-differs")
    result = conffile.classify(str(conf))
    assert result["user_modified"] is True
    assert result["changes_comments_only"] is True
    assert "(Y)" in result["recommendation"]


def test_unknown_stored_md5_defaults_to_keep(tmp_path, monkeypatch):
    conf = _write_pair(tmp_path, "a=1\nb=2\n", "a=1\nb=3\n")
    monkeypatch.setattr(conffile, "_stored_md5", lambda *_: None)
    result = conffile.classify(str(conf))
    assert result["user_modified"] is None
    assert result["stored_md5_known"] is False
    assert "KEEP" in result["recommendation"]


def test_diff_line_count_excludes_headers(tmp_path, monkeypatch):
    conf = _write_pair(tmp_path, "a=1\nb=2\n", "a=1\nb=3\n")
    monkeypatch.setattr(conffile, "_stored_md5", lambda *_: None)
    result = conffile.classify(str(conf))
    # only -b=2 and +b=3 count, not the +++/--- header lines
    assert result["diff_line_count"] == 2
