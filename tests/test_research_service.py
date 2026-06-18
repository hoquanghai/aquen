import pytest

from aquen import research
from aquen.adapters import AdRecord, FakeMetaAdLibraryClient
from aquen.analysis import OriginalityError
from aquen.states import ContentState


def test_add_and_list_competitors(session):
    research.add_competitor(session, "rivalskin", note="main rival")
    research.add_competitor(session, "glowco")
    handles = [c.handle for c in research.list_competitors(session)]
    assert handles == ["rivalskin", "glowco"]


def test_run_research_stores_ads_and_hooks(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "Stop believing this niacinamide myth.")]}
    )
    counts = research.run_research(session, client, limit=10)
    assert counts == {"ads": 1, "hooks": 1}

    hooks = research.list_hooks(session)
    assert len(hooks) == 1
    assert hooks[0].archetype == "myth_bust"
    assert hooks[0].topic == "niacinamide"
    assert hooks[0].source_ad_archive_id == "AD1"


def test_run_research_dedupes_ads(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "Dermatologist tested formula.")]}
    )
    research.run_research(session, client)
    counts = research.run_research(session, client)  # same ad again
    assert counts["ads"] == 0  # already stored


def test_ideate_creates_scripted_item(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "The one niacinamide step everyone skips.")]}
    )
    research.run_research(session, client)
    hook = research.list_hooks(session)[0]

    item = research.ideate(
        session,
        hook.id,
        pillar="derma_decode",
        script="Today let's talk about why a calm, simple barrier routine beats chasing trends.",
    )
    assert item.state == ContentState.SCRIPTED
    assert item.pillar == "derma_decode"
    assert item.hook_archetype == hook.archetype
    assert item.script is not None


def test_ideate_blocks_plagiarised_script(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "The one niacinamide step almost everyone skips today friends")]}
    )
    research.run_research(session, client)
    hook = research.list_hooks(session)[0]

    with pytest.raises(OriginalityError):
        research.ideate(
            session,
            hook.id,
            pillar="derma_decode",
            script="The one niacinamide step almost everyone skips today friends",
        )


def test_ideate_missing_hook_raises(session):
    with pytest.raises(ValueError):
        research.ideate(session, 999, pillar="derma_decode", script="hi")


def test_run_research_dedupes_per_competitor_not_globally(session):
    research.add_competitor(session, "a")
    research.add_competitor(session, "b")
    rec = AdRecord("SAME", "P", "Dermatologist tested barrier serum.")
    client = FakeMetaAdLibraryClient({"a": [rec], "b": [rec]})
    counts = research.run_research(session, client)
    assert counts["ads"] == 2  # one observation per competitor, not globally deduped


def test_add_competitor_duplicate_raises(session):
    research.add_competitor(session, "dup")
    with pytest.raises(ValueError):
        research.add_competitor(session, "dup")


def test_ideate_records_originality_note(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "The one niacinamide step everyone skips.")]}
    )
    research.run_research(session, client)
    hook = research.list_hooks(session)[0]
    item = research.ideate(
        session,
        hook.id,
        pillar="derma_decode",
        script="A calm, simple barrier-first routine beats chasing every new trend.",
    )
    assert item.originality_note == "original"
