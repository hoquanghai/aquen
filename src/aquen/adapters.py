from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AdRecord:
    ad_archive_id: str
    page_name: str
    ad_text: str
    url: str | None = None


class MetaAdLibraryClient(Protocol):
    """Compliant, public-only competitor ad source. Implementations must use official
    APIs / public data only — never scraped follower or customer lists."""

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]: ...


class FakeMetaAdLibraryClient:
    """Deterministic dict-backed client for tests and offline development."""

    def __init__(self, data: dict[str, list[AdRecord]] | None = None) -> None:
        self._data = data or {}

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]:
        return list(self._data.get(handle, []))[:limit]


# Bundled sample ad copy (original, generic) so `aquen research` is demonstrable offline
# without a Meta token. Replace with a live MetaAdLibraryClient when a token is configured.
SAMPLE_ADS: list[AdRecord] = [
    AdRecord("SAMPLE1", "GlowRival", "Stop believing this hydration myth — your barrier needs more than water."),
    AdRecord("SAMPLE2", "DermLab", "Dermatologist-tested: clinically proven to strengthen the skin barrier in 4 weeks."),
    AdRecord("SAMPLE3", "SkinSimple", "5 skincare swaps that finally cleared my dull, tired skin."),
    AdRecord("SAMPLE4", "BarrierCo", "I tracked my skin for 4 weeks — the before and after shocked me."),
    AdRecord("SAMPLE5", "AquaTrend", "The one niacinamide step almost everyone skips."),
]


class SampleMetaAdLibraryClient:
    """Returns the bundled SAMPLE_ADS for any handle. Used as the CLI default until a
    live MetaAdLibraryClient (token-backed) is wired in."""

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]:
        return list(SAMPLE_ADS)[:limit]
