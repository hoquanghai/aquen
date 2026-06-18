from aquen.models import Prompt


def test_prompt_defaults(session):
    p = Prompt(name="mira-clean-portrait", category="avatar", template="a clean portrait of {subject}")
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.id is not None
    assert p.kind == "image"
    assert p.version == 1
    assert p.notes is None
    assert p.created_at is not None


def test_prompt_explicit_fields_roundtrip(session):
    p = Prompt(
        name="mira-grwm",
        category="grwm",
        kind="video",
        template="{subject} does a GRWM with {product}",
        version=3,
        notes="house GRWM v3",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.category == "grwm"
    assert p.kind == "video"
    assert p.version == 3
    assert p.notes == "house GRWM v3"
