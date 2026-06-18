from __future__ import annotations

import re

KNOWN_TOPICS = [
    "beta-glucan",
    "niacinamide",
    "retinol",
    "vitamin c",
    "hyaluronic acid",
    "ceramide",
    "peptide",
    "spf",
    "postbiotic",
    "exosome",
    "hydration",
    "barrier",
]

HOOK_TEMPLATES = {
    "myth_bust": "Stop and rethink: the {topic} 'rule' you were sold is wrong — here's what actually helps.",
    "listicle": "{n} small {topic} swaps that quietly upgraded my skin barrier.",
    "transformation": "I logged my skin for {weeks} weeks with {topic} — here's the honest timeline.",
    "authority": "Here's what the research actually says about {topic} (no hype).",
    "curiosity": "The one {topic} step almost everyone skips.",
}


class OriginalityError(Exception):
    pass


def classify_archetype(ad_text: str) -> str:
    t = ad_text.lower()
    # First match wins; the order encodes precedence:
    # myth_bust > listicle > transformation > authority > curiosity.
    if any(k in t for k in ["myth", "lie", "stop believing", "don't", "do not"]):
        return "myth_bust"
    if re.search(r"\b\d+\s+(ways|steps|things|tips|swaps|reasons)\b", t):
        return "listicle"
    if any(k in t for k in ["before and after", "before/after", "weeks", "results", "transformation"]):
        return "transformation"
    if any(k in t for k in ["dermatologist", "clinically", "science", "study", "proven", "tested"]):
        return "authority"
    return "curiosity"


def extract_topic(ad_text: str) -> str:
    t = ad_text.lower()
    for topic in KNOWN_TOPICS:
        if topic in t:
            return topic
    return "skincare"


def derive_hook(ad_text: str) -> tuple[str, str, str]:
    """Return (house_hook_text, archetype, topic). The hook is an ORIGINAL AQUEN house
    template filled with the inferred topic — it never reuses the source ad's wording."""
    archetype = classify_archetype(ad_text)
    topic = extract_topic(ad_text)
    template = HOOK_TEMPLATES[archetype]
    text = template.format(topic=topic, n=5, weeks=4)
    return text, archetype, topic


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def check_originality(
    source_text: str,
    candidate_text: str,
    n: int = 5,
    jaccard_threshold: float = 0.6,
) -> tuple[bool, str]:
    """Guard against plagiarism: reject a candidate script that shares a long verbatim
    phrase with the source ad, or whose word-set overlaps too heavily."""
    src = _words(source_text)
    cand = _words(candidate_text)
    if _ngrams(src, n) & _ngrams(cand, n):
        return False, f"shares a {n}-word verbatim phrase with the source"
    src_set, cand_set = set(src), set(cand)
    if src_set and cand_set:
        jaccard = len(src_set & cand_set) / len(src_set | cand_set)
        if jaccard >= jaccard_threshold:
            return False, f"word overlap {jaccard:.0%} exceeds the {jaccard_threshold:.0%} limit"
    return True, "original"
