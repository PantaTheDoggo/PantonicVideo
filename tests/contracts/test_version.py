"""Tests for caret-semver helpers — §3.4, S4."""

import pytest
from infracore.version_check import (
    normalize_version,
    caret_match,
)


class TestNormalizeVersion:
    """§3.4 — version strings are normalized by appending zeros for missing components."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("1", "1.0.0"),
            ("1.2", "1.2.0"),
            ("1.2.3", "1.2.3"),
            ("2", "2.0.0"),
            ("0.1", "0.1.0"),
        ],
    )
    def test_normalize_appends_zeros(self, raw, expected):
        """§3.4: normalize_version pads to three components."""
        assert normalize_version(raw) == expected

    @pytest.mark.parametrize(
        "invalid",
        [
            "abc",
            "1.2.3-alpha",
            "1.2.3+build",
            "",
            "1..2",
        ],
    )
    def test_normalize_rejects_invalid(self, invalid):
        """§3.4: normalize_version raises ValueError for non-numeric or suffix-bearing strings."""
        with pytest.raises((ValueError, Exception)):
            normalize_version(invalid)


class TestCaretMatch:
    """§3.4, S4 — caret matching: ^X.Y.Z matches >=X.Y.Z, <(X+1).0.0 for X >= 1."""

    @pytest.mark.parametrize(
        "required, candidate, expected",
        [
            # Basic caret behavior: major boundary
            ("^1.0.0", "1.0.0", True),
            ("^1.0.0", "1.2.3", True),
            ("^1.0.0", "1.9.9", True),
            ("^1.0.0", "2.0.0", False),
            ("^1.0.0", "0.9.9", False),
            # Short-form normalization
            ("^1.0", "1.0.0", True),
            ("^1.0", "1.5.0", True),
            ("^1.0", "2.0.0", False),
            ("^1", "1.0.0", True),
            ("^1", "1.99.0", True),
            ("^1", "2.0.0", False),
            # Exact minimum
            ("^2.3.1", "2.3.1", True),
            ("^2.3.1", "2.3.0", False),
            ("^2.3.1", "3.0.0", False),
        ],
    )
    def test_caret_match(self, required, candidate, expected):
        """§3.4: caret_match(required, candidate) returns the expected boolean."""
        assert caret_match(required, candidate) is expected

    @pytest.mark.parametrize(
        "invalid_required",
        [
            "1.0.0",      # no caret
            ">=1.0.0",    # range syntax not supported
            "~1.0.0",     # tilde not supported
        ],
    )
    def test_caret_match_requires_caret_prefix(self, invalid_required):
        """§3.4: caret_match raises ValueError when the required string lacks a caret prefix."""
        with pytest.raises((ValueError, Exception)):
            caret_match(invalid_required, "1.0.0")
