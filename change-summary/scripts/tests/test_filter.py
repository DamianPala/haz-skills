"""Tests for change_summary.filter: lock files, generated, and binary detection."""

from __future__ import annotations

import pytest

from change_summary.filter import classify_skippable_by_path, is_binary_path


class TestLockFilesSkipped:
    @pytest.mark.parametrize(
        "path",
        [
            "package-lock.json",
            "yarn.lock",
            "Cargo.lock",
            "poetry.lock",
            "go.sum",
            "pnpm-lock.yaml",
        ],
    )
    def test_lock_file_detected(self, path: str) -> None:
        assert classify_skippable_by_path(path) == "lock file"


class TestGeneratedFilesSkipped:
    @pytest.mark.parametrize(
        "path",
        [
            "dist/bundle.min.js",
            "static/style.min.css",
            "proto/service.pb.go",
            "api/types_generated.go",
            "src/schema.generated.ts",
        ],
    )
    def test_generated_file_detected(self, path: str) -> None:
        assert classify_skippable_by_path(path) == "generated"


class TestNormalFilesNotSkipped:
    @pytest.mark.parametrize(
        "path",
        [
            "src/main.py",
            "tests/test_api.py",
            "README.md",
            ".github/workflows/ci.yml",
            "src/utils.ts",
            "docs/guide.md",
        ],
    )
    def test_normal_files_kept(self, path: str) -> None:
        assert classify_skippable_by_path(path) is None

    def test_binary_firmware_flagged(self) -> None:
        assert is_binary_path("firmware/recorder.bin", {}) is True

    def test_hex_file_flagged(self) -> None:
        assert is_binary_path("firmware/app.hex", {}) is True

    def test_source_file_not_binary(self) -> None:
        assert is_binary_path("src/main.c", {"src/main.c": "+code"}) is False
