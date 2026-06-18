from aquen.adapters import (
    AdRecord,
    FakeMetaAdLibraryClient,
    SampleMetaAdLibraryClient,
    SAMPLE_ADS,
)


def test_fake_client_returns_seeded_records():
    rec = AdRecord(ad_archive_id="A1", page_name="Riv", ad_text="hi", url=None)
    client = FakeMetaAdLibraryClient({"riv": [rec]})
    assert client.search("riv") == [rec]
    assert client.search("unknown") == []


def test_fake_client_respects_limit():
    recs = [AdRecord(ad_archive_id=f"A{i}", page_name="p", ad_text="t") for i in range(5)]
    client = FakeMetaAdLibraryClient({"riv": recs})
    assert len(client.search("riv", limit=2)) == 2


def test_sample_client_returns_samples_for_any_handle():
    client = SampleMetaAdLibraryClient()
    out = client.search("anything", limit=3)
    assert len(out) == 3
    assert all(isinstance(r, AdRecord) for r in out)
    assert len(SAMPLE_ADS) >= 3
