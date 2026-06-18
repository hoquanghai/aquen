from aquen.compliance import (
    CheckResult,
    check_ai_disclosure,
    check_ai_label,
    check_commercial_disclosure,
    check_no_prohibited_claims,
    check_substantiation,
    evaluate,
)
from aquen.models import ContentItem


def test_ai_disclosure_pass():
    r = check_ai_disclosure("Created with AI — the science on beta-glucan.")
    assert isinstance(r, CheckResult)
    assert r.name == "ai_disclosure"
    assert r.passed is True


def test_ai_disclosure_fail_when_absent():
    assert check_ai_disclosure("Here's the science on beta-glucan.").passed is False


def test_ai_disclosure_fail_when_none():
    assert check_ai_disclosure(None).passed is False


def test_ai_label_reflects_flag():
    assert check_ai_label(True).passed is True
    assert check_ai_label(False).passed is False


def test_commercial_disclosure_required_only_when_sponsored():
    assert check_commercial_disclosure("no markers here", is_sponsored=False).passed is True
    assert check_commercial_disclosure("no markers here", is_sponsored=True).passed is False
    assert check_commercial_disclosure("paid partnership with X", is_sponsored=True).passed is True


def test_prohibited_testimonial_blocked():
    r = check_no_prohibited_claims("This serum cleared my skin in 2 weeks.", None)
    assert r.passed is False


def test_prohibited_before_after_blocked():
    assert check_no_prohibited_claims("Before and after using Mira's routine.", None).passed is False


def test_prohibited_anti_aging_blocked():
    assert check_no_prohibited_claims(None, "Great anti-aging benefits for everyone.").passed is False


def test_prohibited_clean_caption_passes():
    assert check_no_prohibited_claims("Created with AI. The science on beta-glucan. #ad", "").passed is True


def test_substantiation_required_when_claim_present():
    assert check_substantiation("Clinically supported hydration.", None, None).passed is False
    assert check_substantiation("Clinically supported hydration.", None, "https://study").passed is True


def test_substantiation_not_required_without_claims():
    assert check_substantiation("A calm look at beta-glucan.", None, None).passed is True


def test_evaluate_returns_all_five_checks_in_order():
    item = ContentItem(
        title="t",
        pillar="derma_decode",
        caption="Created with AI. The science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
    )
    results = evaluate(item)
    assert [r.name for r in results] == [
        "ai_disclosure",
        "ai_label",
        "commercial_disclosure",
        "no_prohibited_claims",
        "substantiation",
    ]
    assert all(r.passed for r in results)
