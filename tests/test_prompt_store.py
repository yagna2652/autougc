"""
Unit tests for the PromptStore — SQLite-backed prompt trace storage.

Exercises save_trace, get_trace, list_traces, get_template_versions,
compare_traces, and get_trace_by_job using a temporary DB (no server needed).
"""

from pathlib import Path

import pytest

from src.prompt_store import PromptStore


@pytest.fixture
def store(tmp_path: Path) -> PromptStore:
    """Create a PromptStore backed by a temp database."""
    return PromptStore(db_path=tmp_path / "test_prompts.db")


# ---- Helpers ---------------------------------------------------------------

TEMPLATE_A = "You are an expert. Analyze {{PRODUCT}} and respond in JSON."
TEMPLATE_B = "You are a creative director. Describe {{SCENE}} vividly."


def _make_trace_kwargs(
    template_text: str = TEMPLATE_A,
    job_id: str | None = "job-001",
    **overrides,
) -> dict:
    defaults = dict(
        template_text=template_text,
        assembled_prompt=f"Assembled: {template_text[:40]}...",
        model="openai/gpt-4o-mini",
        inputs_snapshot={"video_analysis": {"style": "casual"}, "product_description": "keychain"},
        job_id=job_id,
        raw_response='{"video_prompt": "test prompt"}',
        processed_output={"video_prompt": "test prompt", "suggested_script": "try this!"},
        token_usage={"input_tokens": 500, "output_tokens": 200},
        latency_ms=1234,
    )
    defaults.update(overrides)
    return defaults


# ---- Tests ------------------------------------------------------------------


class TestSaveAndGetTrace:
    def test_save_returns_uuid(self, store: PromptStore):
        trace_id = store.save_trace(**_make_trace_kwargs())
        assert isinstance(trace_id, str)
        assert len(trace_id) == 36

    def test_roundtrip(self, store: PromptStore):
        trace_id = store.save_trace(**_make_trace_kwargs())
        trace = store.get_trace(trace_id)
        assert trace is not None
        assert trace["trace_id"] == trace_id
        assert trace["job_id"] == "job-001"
        assert trace["model"] == "openai/gpt-4o-mini"
        assert trace["latency_ms"] == 1234
        assert trace["template_version"] == 1
        assert trace["assembled_prompt"].startswith("Assembled:")
        assert trace["raw_response"] == '{"video_prompt": "test prompt"}'

    def test_inputs_snapshot_deserialized(self, store: PromptStore):
        trace_id = store.save_trace(**_make_trace_kwargs())
        trace = store.get_trace(trace_id)
        assert isinstance(trace["inputs_snapshot"], dict)
        assert trace["inputs_snapshot"]["product_description"] == "keychain"

    def test_token_usage_deserialized(self, store: PromptStore):
        trace_id = store.save_trace(**_make_trace_kwargs())
        trace = store.get_trace(trace_id)
        assert isinstance(trace["token_usage"], dict)
        assert trace["token_usage"]["input_tokens"] == 500

    def test_processed_output_deserialized(self, store: PromptStore):
        trace_id = store.save_trace(**_make_trace_kwargs())
        trace = store.get_trace(trace_id)
        assert isinstance(trace["processed_output"], dict)
        assert trace["processed_output"]["video_prompt"] == "test prompt"

    def test_get_nonexistent_returns_none(self, store: PromptStore):
        assert store.get_trace("nonexistent-id") is None

    def test_nullable_fields(self, store: PromptStore):
        trace_id = store.save_trace(
            template_text=TEMPLATE_A,
            assembled_prompt="bare minimum",
            model="test-model",
            inputs_snapshot={},
            job_id=None,
            raw_response=None,
            processed_output=None,
            token_usage=None,
            latency_ms=None,
        )
        trace = store.get_trace(trace_id)
        assert trace is not None
        assert trace["job_id"] is None
        assert trace["raw_response"] is None
        assert trace["processed_output"] is None
        assert trace["token_usage"] is None
        assert trace["latency_ms"] is None


class TestTemplateVersioning:
    def test_same_template_same_version(self, store: PromptStore):
        id1 = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        id2 = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        t1 = store.get_trace(id1)
        t2 = store.get_trace(id2)
        assert t1["template_version"] == t2["template_version"] == 1

    def test_different_template_increments_version(self, store: PromptStore):
        id1 = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        id2 = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_B))
        t1 = store.get_trace(id1)
        t2 = store.get_trace(id2)
        assert t1["template_version"] == 1
        assert t2["template_version"] == 2

    def test_hash_is_deterministic(self, store: PromptStore):
        h1 = PromptStore.hash_template(TEMPLATE_A)
        h2 = PromptStore.hash_template(TEMPLATE_A)
        h3 = PromptStore.hash_template(TEMPLATE_B)
        assert h1 == h2
        assert h1 != h3


class TestGetTemplateVersions:
    def test_empty_store(self, store: PromptStore):
        assert store.get_template_versions() == []

    def test_counts_traces_per_version(self, store: PromptStore):
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_B))
        versions = store.get_template_versions()
        assert len(versions) == 2
        # Ordered DESC: v2 first
        assert versions[0]["version_number"] == 2
        assert versions[0]["run_count"] == 1
        assert versions[1]["version_number"] == 1
        assert versions[1]["run_count"] == 2


class TestListTraces:
    def test_empty_store(self, store: PromptStore):
        assert store.list_traces() == []

    def test_returns_summaries_without_large_fields(self, store: PromptStore):
        store.save_trace(**_make_trace_kwargs())
        traces = store.list_traces()
        assert len(traces) == 1
        t = traces[0]
        assert "trace_id" in t
        assert "template_version" in t
        assert "assembled_prompt" not in t
        assert "raw_response" not in t

    def test_pagination(self, store: PromptStore):
        for i in range(5):
            store.save_trace(**_make_trace_kwargs(job_id=f"job-{i:03d}"))
        assert len(store.list_traces(limit=2, offset=0)) == 2
        assert len(store.list_traces(limit=2, offset=2)) == 2
        assert len(store.list_traces(limit=2, offset=4)) == 1

    def test_filter_by_template_version(self, store: PromptStore):
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_B))
        store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A))
        assert len(store.list_traces(template_version=1)) == 2
        assert len(store.list_traces(template_version=2)) == 1

    def test_filter_by_job_id(self, store: PromptStore):
        store.save_trace(**_make_trace_kwargs(job_id="job-alpha"))
        store.save_trace(**_make_trace_kwargs(job_id="job-beta"))
        store.save_trace(**_make_trace_kwargs(job_id="job-alpha"))
        assert len(store.list_traces(job_id="job-alpha")) == 2
        assert len(store.list_traces(job_id="job-beta")) == 1

    def test_ordering_newest_first(self, store: PromptStore):
        id1 = store.save_trace(**_make_trace_kwargs(job_id="first"))
        id2 = store.save_trace(**_make_trace_kwargs(job_id="second"))
        traces = store.list_traces()
        assert traces[0]["trace_id"] == id2
        assert traces[1]["trace_id"] == id1


class TestCompareTraces:
    def test_compare_two_traces(self, store: PromptStore):
        id_a = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_A, job_id="job-a"))
        id_b = store.save_trace(**_make_trace_kwargs(template_text=TEMPLATE_B, job_id="job-b"))
        result = store.compare_traces(id_a, id_b)
        assert result is not None
        assert result["a"]["trace_id"] == id_a
        assert result["b"]["trace_id"] == id_b
        assert result["a"]["template_version"] == 1
        assert result["b"]["template_version"] == 2

    def test_returns_none_for_missing(self, store: PromptStore):
        id_a = store.save_trace(**_make_trace_kwargs())
        assert store.compare_traces(id_a, "nonexistent") is None
        assert store.compare_traces("nonexistent", id_a) is None


class TestGetTraceByJob:
    def test_returns_latest_for_job(self, store: PromptStore):
        store.save_trace(**_make_trace_kwargs(job_id="job-x", latency_ms=100))
        id2 = store.save_trace(**_make_trace_kwargs(job_id="job-x", latency_ms=200))
        trace = store.get_trace_by_job("job-x")
        assert trace is not None
        assert trace["trace_id"] == id2
        assert trace["latency_ms"] == 200

    def test_returns_none_for_unknown_job(self, store: PromptStore):
        assert store.get_trace_by_job("nonexistent") is None


class TestDatabaseCreation:
    def test_creates_db_file(self, tmp_path: Path):
        db_path = tmp_path / "subdir" / "nested" / "prompts.db"
        PromptStore(db_path=db_path)
        assert db_path.exists()

    def test_idempotent_init(self, tmp_path: Path):
        db_path = tmp_path / "prompts.db"
        store1 = PromptStore(db_path=db_path)
        store1.save_trace(**_make_trace_kwargs())
        store2 = PromptStore(db_path=db_path)
        assert len(store2.list_traces()) == 1
