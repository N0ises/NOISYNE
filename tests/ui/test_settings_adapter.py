from __future__ import annotations

from brain.ui.adapters.v1 import V1ApplicationAdapter


def test_v1_settings_snapshot_exposes_effective_configuration_read_only(
    product_metadata,
) -> None:
    snapshot = V1ApplicationAdapter(metadata=product_metadata).settings_snapshot()
    values = {item.key: item for item in snapshot.values}

    assert snapshot.source == "packaged_default"
    assert snapshot.revision == "packaged-v1"
    assert snapshot.credential_configured
    assert {
        "llm.provider",
        "llm.model",
        "llm.base_url",
        "runtime.device",
        "runtime.model_root",
        "models.clap.name",
        "models.bge_reranker.name",
        "audio.sample_rate",
        "chroma.path",
        "chroma.collection",
        "embedding.model_path",
        "runtime.report_dir",
        "runtime.cache_dir",
        "runtime.model_cache_dir",
        "runtime.log_dir",
        "logging.level",
        "logging.format",
    } <= values.keys()
    assert all(not item.writable for item in snapshot.values)
    assert all(not item.restart_required for item in snapshot.values)
    assert all(item.read_only_reason for item in snapshot.values)


def test_v1_settings_snapshot_never_exposes_secret_value_or_key_name(product_metadata) -> None:
    snapshot = V1ApplicationAdapter(metadata=product_metadata).settings_snapshot()
    serialized = repr(snapshot)

    assert "api_key" not in serialized
    assert "lm-studio" not in serialized
