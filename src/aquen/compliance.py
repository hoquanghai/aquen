from __future__ import annotations

import re
from dataclasses import dataclass

from sqlmodel import Session, select

from aquen.models import ComplianceCheck, ContentItem

# Mira is a synthetic performer, so an AI disclosure is required on every post.
AI_DISCLOSURE_MARKERS = [
    "ai-generated",
    "ai generated",
    "created with ai",
    "made with ai",
    "generated with ai",
    "ai avatar",
    "synthetic",
    "virtual creator",
]

# A commercial-relationship disclosure is required only on sponsored/branded posts.
COMMERCIAL_MARKERS = [
    "#ad",
    "paid partnership",
    "paid promotion",
    "sponsored",
    "advertisement",
]

# Skincare claim language that must be backed by a substantiation source.
CLAIM_MARKERS = [
    "clinically",
    "clinical",
    "proven",
    "reduces",
    "boosts",
    "increases",
    "strengthens",
    "repairs",
    "dermatologist-tested",
    "%",
]

# Flatly prohibited regardless of disclosure (spec §4.5): AI testimonials, before/after,
# fabricated efficacy, "anti-aging". First match wins.
PROHIBITED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"before\s*(?:and|/|&|-)\s*after", re.IGNORECASE),
        "before/after results are prohibited",
    ),
    (
        re.compile(
            r"\b(?:cleared|healed|fixed|cured|transformed|improved)\b[^.?!]{0,25}\b(?:skin|acne|breakouts?)\b",
            re.IGNORECASE,
        ),
        "AI testimonial / efficacy claim is prohibited",
    ),
    (
        re.compile(r"got rid of[^.?!]{0,25}\b(?:acne|breakouts?|pimples?)\b", re.IGNORECASE),
        "efficacy claim is prohibited",
    ),
    (
        re.compile(r"anti[\s-]?aging", re.IGNORECASE),
        "'anti-aging' claim is prohibited",
    ),
]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _find_marker(text: str | None, markers: list[str]) -> str | None:
    t = (text or "").lower()
    return next((m for m in markers if m in t), None)


def check_ai_disclosure(caption: str | None) -> CheckResult:
    marker = _find_marker(caption, AI_DISCLOSURE_MARKERS)
    if marker:
        return CheckResult("ai_disclosure", True, f"AI disclosure present ('{marker}')")
    return CheckResult(
        "ai_disclosure", False, "caption is missing an 'AI-generated' disclosure"
    )


def check_ai_label(ai_label_on_content: bool) -> CheckResult:
    if ai_label_on_content:
        return CheckResult("ai_label", True, "persistent on-content AI label confirmed")
    return CheckResult(
        "ai_label", False, "persistent on-content AI label not confirmed"
    )


def check_commercial_disclosure(caption: str | None, is_sponsored: bool) -> CheckResult:
    if not is_sponsored:
        return CheckResult(
            "commercial_disclosure", True, "not a sponsored post — disclosure not required"
        )
    marker = _find_marker(caption, COMMERCIAL_MARKERS)
    if marker:
        return CheckResult(
            "commercial_disclosure", True, f"commercial disclosure present ('{marker}')"
        )
    return CheckResult(
        "commercial_disclosure",
        False,
        "sponsored post is missing a commercial-relationship disclosure (#ad alone is not enough)",
    )


def check_no_prohibited_claims(caption: str | None, script: str | None) -> CheckResult:
    blob = f"{caption or ''} {script or ''}"
    for pattern, reason in PROHIBITED_PATTERNS:
        if pattern.search(blob):
            return CheckResult("no_prohibited_claims", False, reason)
    return CheckResult("no_prohibited_claims", True, "no prohibited claims found")


def check_substantiation(
    caption: str | None, script: str | None, substantiation_url: str | None
) -> CheckResult:
    marker = _find_marker(f"{caption or ''} {script or ''}", CLAIM_MARKERS)
    if marker and not substantiation_url:
        return CheckResult(
            "substantiation",
            False,
            f"claim language ('{marker}') needs a substantiation source",
        )
    return CheckResult("substantiation", True, "claims substantiated or none made")


def evaluate(item: ContentItem) -> list[CheckResult]:
    """Run all five compliance checks against a content item (pure, no DB)."""
    return [
        check_ai_disclosure(item.caption),
        check_ai_label(item.ai_label_on_content),
        check_commercial_disclosure(item.caption, item.is_sponsored),
        check_no_prohibited_claims(item.caption, item.script),
        check_substantiation(item.caption, item.script, item.substantiation_url),
    ]


class ComplianceError(Exception):
    pass


def record_checks(session: Session, item_id: int) -> list[ComplianceCheck]:
    """Run the gate on a content item and persist one ComplianceCheck row per check."""
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")
    rows = [
        ComplianceCheck(
            content_item_id=item_id, check=r.name, passed=r.passed, detail=r.detail
        )
        for r in evaluate(item)
    ]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def assert_compliant(session: Session, item_id: int) -> list[ComplianceCheck]:
    """Record the checks; raise ComplianceError listing every failure if any check fails."""
    rows = record_checks(session, item_id)
    failed = [r for r in rows if not r.passed]
    if failed:
        summary = "; ".join(f"{r.check}: {r.detail}" for r in failed)
        raise ComplianceError(f"content {item_id} is not ready — {summary}")
    return rows


def list_checks(session: Session, item_id: int) -> list[ComplianceCheck]:
    stmt = (
        select(ComplianceCheck)
        .where(ComplianceCheck.content_item_id == item_id)
        .order_by(ComplianceCheck.id)
    )
    return list(session.exec(stmt))
