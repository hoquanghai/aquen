import pytest

from aquen.analysis import (
    OriginalityError,
    check_originality,
    classify_archetype,
    derive_hook,
    extract_topic,
)


def test_classify_archetype():
    assert classify_archetype("Stop believing this myth") == "myth_bust"
    assert classify_archetype("5 swaps that changed my skin") == "listicle"
    assert classify_archetype("My before and after after 4 weeks") == "transformation"
    assert classify_archetype("Dermatologist-tested and clinically proven") == "authority"
    assert classify_archetype("A calm everyday glow") == "curiosity"


def test_extract_topic_prefers_known_ingredient():
    assert extract_topic("more niacinamide for your barrier") == "niacinamide"
    assert extract_topic("just a nice glow") == "skincare"


def test_derive_hook_uses_house_template_not_source_words():
    text, archetype, topic = derive_hook("Stop believing this niacinamide myth!!!")
    assert archetype == "myth_bust"
    assert topic == "niacinamide"
    # House template, original phrasing — does NOT copy the source verbatim
    assert "Stop believing this niacinamide myth" not in text
    assert "niacinamide" in text


def test_check_originality_passes_for_distinct_text():
    ok, reason = check_originality(
        "Stop believing this hydration myth your barrier needs oil",
        "Here is a totally different script about ceramides and calm routines",
    )
    assert ok is True


def test_check_originality_fails_on_verbatim_phrase():
    src = "your skin barrier needs more than water to stay healthy and strong"
    ok, reason = check_originality(src, "honestly your skin barrier needs more than water friends")
    assert ok is False
    assert "verbatim" in reason


def test_check_originality_fails_on_high_overlap():
    src = "barrier repair hydration glow serum routine niacinamide ceramide dewy skin"
    cand = "barrier repair hydration glow serum routine niacinamide ceramide dewy skin today"
    ok, reason = check_originality(src, cand)
    assert ok is False


def test_originality_error_is_exception():
    assert issubclass(OriginalityError, Exception)
