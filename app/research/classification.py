"""Source classification and freshness weighting for research (Phase 4).

Determines ``Source.source_type`` (primary/official/secondary/community/
unverified) and a freshness score using pure, deterministic heuristics — no
DB, no LLM, no network. This keeps "how trustworthy is this source" auditable
and testable rather than delegating it to model-generated text (AGENS.md rule 273).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.schemas.research import Source

# --------------------------------------------------------------------------- #
# Domain classification heuristics
# --------------------------------------------------------------------------- #

#: Exact hosts that are primary/official publishers (standards, academia, medicine).
_OFFICIAL_EXACT_HOSTS = {
    "w3.org",
    "ietf.org",
    "iso.org",
    "ieee.org",
    "ncbi.nlm.nih.gov",
    "arxiv.org",
    "docs.python.org",
    "docs.microsoft.com",
    "developer.mozilla.org",
}

#: TLDs that are reliably official (accredited institutions).
_OFFICIAL_TLDS = (".edu",)

#: News / trade publications — reputable secondary sources.
_SECONDARY_HOST_KEYWORDS = (
    "reuters", "ap.org", "bloomberg", "wsj.com", "ft.com", "techcrunch",
    "arstechnica", "theverge", "wired", "zdnet", "theregister",
    "infosecurity-magazine", "engadget", "techradar", "theeconomist",
)

#: Community / opinion / social hosts.
_COMMUNITY_HOST_KEYWORDS = (
    "reddit", "twitter", "x.com", "hacker-news", "news.ycombinator",
    "dev.to", "medium.com", "substack", "linkedin.com", "quora",
)

#: TLDs treated as community (user-generated content / disposable).
_COMMUNITY_TLDS = (".tk", ".ml", ".ga", ".cf")

# A lightweight extraction of the registrable domain for heuristics. We do NOT
# do full Public-Suffix-List resolution (that would add an external dep); the
# heuristics below are intentionally conservative and err toward "unverified".
_SUFFIX_RE = re.compile(r"([a-z0-9-]+\.[a-z]{2,})$", re.IGNORECASE)
_TLD_RE = re.compile(r"\.([a-z]{2,})$", re.IGNORECASE)

# --------------------------------------------------------------------------- #
# Freshness
# --------------------------------------------------------------------------- #

#: Half-life in days for the freshness decay.
FRESHNESS_HALFLIFE_DAYS: float = 7.0


def classify_source(url: str | None, title: str | None = None) -> str:
    """Classify a source URL into a :class:`SourceType` bucket.

    The classification is deliberately conservative: unknown hosts are
    ``unverified`` rather than guessed, so the pipeline never overstates a
    source's authority.
    """
    if not url:
        return "unverified"

    host = _extract_host(url)
    if not host:
        return "unverified"

    host_lower = host.lower()
    suffix = _last_suffix(host_lower)
    tld = _tld(host_lower)

    # Primary: government / intergovernmental (incl. multi-part ccTLDs like
    # .gov.uk, .gov.au, .gc.ca — matched via the two-segment suffix).
    if (
        tld in ("gov", "gouv")
        or suffix in ("gov.uk", "gov.au", "gc.ca")
        or host_lower.endswith(".gc.ca")
    ):
        return "primary"

    # Official: exact-listed publisher hosts or .edu accredited institutions.
    if host_lower in _OFFICIAL_EXACT_HOSTS or host_lower.endswith(_OFFICIAL_TLDS):
        return "official"

    # Secondary: recognised news/trade publishers.
    if any(kw in host_lower for kw in _SECONDARY_HOST_KEYWORDS):
        return "secondary"

    # Community: user-generated / social platforms, or disposable TLDs.
    if any(kw in host_lower for kw in _COMMUNITY_HOST_KEYWORDS) or suffix in _COMMUNITY_TLDS:
        return "community"

    # Anything else is unverified.
    return "unverified"


def classify_source_obj(source: Source) -> Source:
    """Return a copy of *source* with ``source_type`` populated by heuristics."""
    return source.model_copy(update={"source_type": classify_source(source.url, source.title)})


def freshness_score(
    published_at: datetime | None,
    reference: datetime | None = None,
) -> float:
    """Return a ``[0.0, 1.0]`` freshness score for a publication timestamp.

    Uses exponential decay with a 7-day half-life (AGENS.md rule 92): a source
    published "now" scores 1.0; older sources decay smoothly toward 0.0.
    An ``None`` published_at yields ``0.0`` (undated → no freshness claim).
    """
    if published_at is None:
        return 0.0

    ref = reference or datetime.now(UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)

    age_days = max(0.0, (ref - published_at).total_seconds() / 86400.0)
    return float(2 ** (-age_days / FRESHNESS_HALFLIFE_DAYS))


def sort_by_confidence_and_freshness(sources: list[Source]) -> list[Source]:
    """Rank sources: primary/official first, then by freshness.

    A cheap deterministic comparator used by the pipeline to order candidate
    sources before spending model budget on extraction.
    """
    _rank = {
        "primary": 0,
        "official": 1,
        "secondary": 2,
        "community": 3,
        "unverified": 4,
    }

    def _key(s: Source) -> tuple[int, float]:
        return (_rank[s.source_type], freshness_score(s.published_at))

    return sorted(sources, key=_key)


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #

def _extract_host(url: str) -> str | None:
    # Strip scheme and path — tolerate whitespace/garbage.
    stripped = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", url.strip())
    # Remove path/query/fragment.
    stripped = stripped.split("/", 1)[0]
    stripped = stripped.split("?", 1)[0]
    # Strip userinfo if present.
    if "@" in stripped:
        stripped = stripped.rsplit("@", 1)[-1]
    return stripped or None


def _last_suffix(host: str) -> str:
    match = _SUFFIX_RE.search(host)
    return match.group(1) if match else ""


def _tld(host: str) -> str:
    match = _TLD_RE.search(host)
    return match.group(1) if match else ""
