"""Unit tests for app.research.classification (Phase 4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.research.classification import (
    FRESHNESS_HALFLIFE_DAYS,
    classify_source,
    classify_source_obj,
    freshness_score,
    sort_by_confidence_and_freshness,
)
from app.schemas.research import Source

# --------------------------------------------------------------------------- #
# classify_source
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.whitehouse.gov/", "primary"),
        ("http://europa.eu/gov/", "unverified"),  # .eu → unverified
        ("https://www.parl.gc.ca/", "primary"),
        ("https://data.gov/", "primary"),
        ("https://www.gov.uk/", "primary"),
    ],
)
def test_primary_sources(url: str, expected: str) -> None:
    assert classify_source(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://w3.org/TR/whatwg-fetch/", "official"),
        ("https://ietf.org/rfc/9110", "official"),
        ("https://arxiv.org/abs/2401.0001", "official"),
        ("https://mit.edu/", "official"),  # .edu
        ("https://cs.stanford.edu/~foo", "official"),
    ],
)
def test_official_sources(url: str, expected: str) -> None:
    assert classify_source(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.reuters.com/world/", "secondary"),
        ("https://www.theverge.com/2024/1/1", "secondary"),
        ("https://techcrunch.com/2024/01/01", "secondary"),
        ("https://www.bloomberg.com/news", "secondary"),
        ("https://www.wired.com/story", "secondary"),
    ],
)
def test_secondary_sources(url: str, expected: str) -> None:
    assert classify_source(url) == expected


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.reddit.com/r/programming/", "community"),
        ("https://x.com/user/status/1", "community"),
        ("https://news.ycombinator.com/item?id=1", "community"),
        ("https://medium.com/@user/post-1", "community"),
        ("https://dev.to/user/post", "community"),
    ],
)
def test_community_sources(url: str, expected: str) -> None:
    assert classify_source(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://myblog.example.com/",
        "https://somefreewebsite.tk/",
        None,
        "",
        "not-a-url",
        "ftp://example.com",
    ],
)
def test_unverified_sources(url: str | None) -> None:
    assert classify_source(url) == "unverified"


def test_classify_source_ignores_title() -> None:
    # The title argument is reserved for future heuristics; it must not change
    # a clearly-government URL's classification.
    assert classify_source("https://www.cdc.gov/", title="CDC") == "primary"


# --------------------------------------------------------------------------- #
# classify_source_obj
# --------------------------------------------------------------------------- #


def test_classify_source_obj_populates_and_returns_copy() -> None:
    s = Source(url="https://arxiv.org/abs/123", source_type="unverified")
    classified = classify_source_obj(s)
    assert classified.source_type == "official"
    # Original is untouched.
    assert s.source_type == "unverified"


# --------------------------------------------------------------------------- #
# freshness_score
# --------------------------------------------------------------------------- #


def test_freshness_score_now_is_one() -> None:
    ref = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    assert freshness_score(ref, reference=ref) == pytest.approx(1.0)


def test_freshness_score_none_is_zero() -> None:
    assert freshness_score(None) == 0.0


def test_freshness_score_halflife_decays() -> None:
    ref = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    published = ref - timedelta(days=FRESHNESS_HALFLIFE_DAYS)
    assert freshness_score(published, reference=ref) == pytest.approx(0.5)


def test_freshness_score_old_is_zeroish() -> None:
    ref = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    published = ref - timedelta(days=365 * 2)
    # 2 years old → effectively 0 (well under 1e-6).
    assert freshness_score(published, reference=ref) < 1e-3


def test_freshness_score_naive_tz_aware_now() -> None:
    ref = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    published = ref - timedelta(days=14)  # two half-lives → 0.25
    naive = published.replace(tzinfo=None)
    assert freshness_score(naive, reference=ref) == pytest.approx(0.25)


# --------------------------------------------------------------------------- #
# sort_by_confidence_and_freshness
# --------------------------------------------------------------------------- #


def test_sort_ranks_primary_before_community() -> None:
    ref = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    sources = [
        Source(url="https://reddit.com/x", source_type="community", retrieved_at=ref),
        Source(url="https://arxiv.org/a", source_type="official", retrieved_at=ref),
        Source(url="https://myblog.example.com", source_type="unverified", retrieved_at=ref),
    ]
    ranked = sort_by_confidence_and_freshness(sources)
    assert ranked[0].url == "https://arxiv.org/a"
    assert ranked[-1].url == "https://myblog.example.com"
