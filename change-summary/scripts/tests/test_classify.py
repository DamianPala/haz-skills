"""Tests for change_summary.classify: file categorization."""

from __future__ import annotations

import pytest

from change_summary.classify import categorize_file


class TestFileCategorization:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("src/main.py", "source"),
            ("lib/utils.js", "source"),
            ("app/core.ts", "source"),
            ("server.go", "source"),
            ("main.rs", "source"),
        ],
    )
    def test_source_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("tests/test_main.py", "test"),
            ("test/unit_test.js", "test"),
            ("src/main_test.go", "test"),
            ("src/utils.spec.ts", "test"),
        ],
    )
    def test_test_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("README.md", "docs"),
            ("docs/usage.md", "docs"),
            ("CONTRIBUTING.rst", "docs"),
        ],
    )
    def test_docs_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            (".github/workflows/ci.yml", "ci"),
            ("Makefile", "ci"),
            ("Dockerfile", "ci"),
        ],
    )
    def test_ci_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("requirements.txt", "deps"),
            ("package-lock.json", "deps"),
            ("yarn.lock", "deps"),
        ],
    )
    def test_deps_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("logo.png", "assets"),
            ("fonts/roboto.woff2", "assets"),
            ("images/hero.jpg", "assets"),
        ],
    )
    def test_assets_files(self, path: str, expected: str) -> None:
        assert categorize_file(path) == expected

    def test_root_config(self) -> None:
        assert categorize_file("config.yml") == "config"

    def test_nested_config_is_other(self) -> None:
        assert categorize_file("nested/config.yml") == "other"
