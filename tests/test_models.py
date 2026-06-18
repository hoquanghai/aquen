from aquen.models import ContentItem
from aquen.states import ContentState


def test_content_item_defaults(session):
    item = ContentItem(title="Beta-glucan 101", pillar="derma_decode")
    session.add(item)
    session.commit()
    session.refresh(item)

    assert item.id is not None
    assert item.state == ContentState.IDEA
    assert item.created_at is not None
