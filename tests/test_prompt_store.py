"""
Unit tests for the PromptStore — content-addressable prompt versioning.

Covers: save/get versions, content-addressable hashing, trace CRUD,
label CRUD, list_versions with aggregated data.
"""

from pathlib import Path

import pytest

from src.prompt_store import PromptStore


@pytest.fixture
def store(tmp_path: Path) -> PromptStore:
    return PromptStore(db_path=tmp_path / "test_prompts.db")


PROMPT_A = "Close-up of a hand holding @Element1 vertically."
PROMPT_B = "Wide shot of @Element1 on a table, camera slowly zooms in."
NEG_A = "blur, distort"
NEG_B = "low quality, shaky"


class TestContentAddressableHashing:
    def test_same_text_same_hash(self):
        h1 = PromptStore.hash_prompt(PROMPT_A, NEG_A)
        h2 = PromptStore.hash_prompt(PROMPT_A, NEG_A)
        assert h1 == h2

    def test_different_prompt_different_hash(self):
        h1 = PromptStore.hash_prompt(PROMPT_A, NEG_A)
        h2 = PromptStore.hash_prompt(PROMPT_B, NEG_A)
        assert h1 != h2

    def test_different_negative_different_hash(self):
        h1 = PromptStore.hash_prompt(PROMPT_A, NEG_A)
        h2 = PromptStore.hash_prompt(PROMPT_A, NEG_B)
        assert h1 != h2

    def test_hash_is_sha256_hex(self):
        h = PromptStore.hash_prompt(PROMPT_A)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSaveVersion:
    def test_returns_new_version(self, store: PromptStore):
        result = store.save_version(PROMPT_A, NEG_A)
        assert result["is_new"] is True
        assert result["version"] == 1
        assert len(result["id"]) == 36  # UUID

    def test_same_text_returns_existing(self, store: PromptStore):
        r1 = store.save_version(PROMPT_A, NEG_A)
        r2 = store.save_version(PROMPT_A, NEG_A)
        assert r1["id"] == r2["id"]
        assert r2["is_new"] is False
        assert r2["version"] == 1

    def test_different_text_increments_version(self, store: PromptStore):
        r1 = store.save_version(PROMPT_A)
        r2 = store.save_version(PROMPT_B)
        assert r1["version"] == 1
        assert r2["version"] == 2
        assert r1["id"] != r2["id"]

    def test_saves_optional_fields(self, store: PromptStore):
        result = store.save_version(
            PROMPT_A, NEG_A,
            name="soft lighting v2",
            change_note="increased motion",
            model_config={"duration": 5, "aspect_ratio": "9:16"},
        )
        version = store.get_version(result["id"])
        assert version is not None
        assert version["name"] == "soft lighting v2"
        assert version["change_note"] == "increased motion"
        assert version["model_config"]["duration"] == 5


class TestGetVersion:
    def test_roundtrip(self, store: PromptStore):
        r = store.save_version(PROMPT_A, NEG_A, name="test")
        v = store.get_version(r["id"])
        assert v is not None
        assert v["prompt"] == PROMPT_A
        assert v["negative_prompt"] == NEG_A
        assert v["version"] == 1
        assert v["name"] == "test"

    def test_nonexistent_returns_none(self, store: PromptStore):
        assert store.get_version("nonexistent-id") is None


class TestListVersions:
    def test_empty_store(self, store: PromptStore):
        assert store.list_versions() == []

    def test_returns_summaries_ordered_desc(self, store: PromptStore):
        store.save_version(PROMPT_A)
        store.save_version(PROMPT_B)
        versions = store.list_versions()
        assert len(versions) == 2
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    def test_prompt_preview_truncated(self, store: PromptStore):
        long_prompt = "x" * 200
        store.save_version(long_prompt)
        versions = store.list_versions()
        assert len(versions[0]["prompt_preview"]) == 80

    def test_trace_count_and_avg_rating(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        t1 = store.save_trace(r["id"], status="success")
        t2 = store.save_trace(r["id"], status="success")
        store.update_trace(t1, rating=1)
        store.update_trace(t2, rating=-1)
        versions = store.list_versions()
        assert versions[0]["trace_count"] == 2
        assert versions[0]["avg_rating"] == 0.0

    def test_labels_included(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        store.set_label("favorite", r["id"])
        versions = store.list_versions()
        assert "favorite" in versions[0]["labels"]

    def test_pagination(self, store: PromptStore):
        for i in range(5):
            store.save_version(f"prompt {i}")
        assert len(store.list_versions(limit=2, offset=0)) == 2
        assert len(store.list_versions(limit=2, offset=4)) == 1


class TestTraces:
    def test_save_and_get_traces(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        tid = store.save_trace(
            r["id"],
            job_id="job-001",
            start_image_url="http://img.png",
            product_images=["a.png", "b.png"],
            status="pending",
        )
        assert len(tid) == 36

        traces = store.get_traces(r["id"])
        assert len(traces) == 1
        t = traces[0]
        assert t["job_id"] == "job-001"
        assert t["status"] == "pending"
        assert t["product_images"] == ["a.png", "b.png"]

    def test_update_trace(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        tid = store.save_trace(r["id"], status="pending")
        store.update_trace(tid, video_url="http://vid.mp4", elapsed_seconds=120.5, status="success")
        t = store.get_trace(tid)
        assert t is not None
        assert t["video_url"] == "http://vid.mp4"
        assert t["elapsed_seconds"] == 120.5
        assert t["status"] == "success"

    def test_update_rating_and_notes(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        tid = store.save_trace(r["id"], status="success")
        store.update_trace(tid, rating=1, notes="great motion")
        t = store.get_trace(tid)
        assert t["rating"] == 1
        assert t["notes"] == "great motion"

    def test_multiple_traces_same_version(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        store.save_trace(r["id"], job_id="a", status="success")
        store.save_trace(r["id"], job_id="b", status="error", error_message="timeout")
        traces = store.get_traces(r["id"])
        assert len(traces) == 2

    def test_get_nonexistent_trace(self, store: PromptStore):
        assert store.get_trace("nonexistent") is None

    def test_traces_ordered_newest_first(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        t1 = store.save_trace(r["id"], job_id="first", status="success")
        t2 = store.save_trace(r["id"], job_id="second", status="success")
        traces = store.get_traces(r["id"])
        assert traces[0]["id"] == t2
        assert traces[1]["id"] == t1


class TestLabels:
    def test_set_and_list(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        store.set_label("favorite", r["id"])
        labels = store.list_labels()
        assert len(labels) == 1
        assert labels[0]["name"] == "favorite"
        assert labels[0]["prompt_version_id"] == r["id"]

    def test_move_label_to_different_version(self, store: PromptStore):
        r1 = store.save_version(PROMPT_A)
        r2 = store.save_version(PROMPT_B)
        store.set_label("best", r1["id"])
        store.set_label("best", r2["id"])
        labels = store.list_labels()
        assert len(labels) == 1
        assert labels[0]["prompt_version_id"] == r2["id"]

    def test_remove_label(self, store: PromptStore):
        r = store.save_version(PROMPT_A)
        store.set_label("favorite", r["id"])
        store.remove_label("favorite")
        assert store.list_labels() == []

    def test_remove_nonexistent_label(self, store: PromptStore):
        store.remove_label("nonexistent")  # should not raise


class TestDatabaseCreation:
    def test_creates_db_file(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "nested" / "prompts.db"
        PromptStore(db_path=db_path)
        assert db_path.exists()

    def test_idempotent_init(self, tmp_path: Path):
        db_path = tmp_path / "prompts.db"
        store1 = PromptStore(db_path=db_path)
        store1.save_version(PROMPT_A)
        store2 = PromptStore(db_path=db_path)
        assert len(store2.list_versions()) == 1
