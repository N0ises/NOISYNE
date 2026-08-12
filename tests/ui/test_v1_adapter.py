from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from brain.ui.adapters.v1 import V1ApplicationAdapter
from brain.ui.contracts import (
    AnalysisCommand,
    Availability,
    CapabilityLifecycle,
)


@dataclass
class FakeAnalysis:
    loudness: float = -14.0
    nested: list[str] | None = None


class FakeSoundBrainService:
    def analyze(self, _request):
        report = SimpleNamespace(
            audio_type="full_mix",
            score=87.5,
            ai_summary="Summary",
            issues=[
                SimpleNamespace(
                    title="Issue",
                    severity="medium",
                    description="Description",
                    recommendation="Recommendation",
                )
            ],
        )
        return SimpleNamespace(
            report=report,
            analysis=FakeAnalysis(),
            comparison=SimpleNamespace(similarity=91.0),
            status="degraded",
            warnings=["Optional stage unavailable"],
        )


def test_v1_adapter_flattens_domain_response(product_metadata, tmp_path) -> None:
    adapter = V1ApplicationAdapter(
        metadata=product_metadata,
        service_factory=FakeSoundBrainService,
    )

    output = tmp_path / "analysis.json"
    output.write_text("{}", encoding="utf-8")
    result = adapter.analyze(AnalysisCommand(source_path=Path("mix.wav"), output_path=output))

    assert result.audio_type == "full_mix"
    assert result.score == 87.5
    assert result.reference_similarity == 91.0
    assert result.warnings == ("Optional stage unavailable",)
    assert result.metrics[0].name == "loudness"
    assert result.metrics[0].value == -14.0
    assert result.issues[0].title == "Issue"
    assert result.reports[0].source_path == Path("mix.wav")


def test_capability_snapshot_does_not_infer_machine_readiness(product_metadata) -> None:
    adapter = V1ApplicationAdapter(metadata=product_metadata)
    snapshots = {item.id: item for item in adapter.capability_snapshots()}

    assert snapshots["dsp_analysis"].lifecycle is CapabilityLifecycle.PRODUCTION
    assert snapshots["dsp_analysis"].availability is Availability.UNKNOWN
    assert snapshots["audio_intelligence"].lifecycle is CapabilityLifecycle.PLANNED
    assert snapshots["audio_intelligence"].availability is Availability.UNAVAILABLE


def test_settings_snapshot_is_read_only_and_redacted(product_metadata) -> None:
    snapshot = V1ApplicationAdapter(metadata=product_metadata).settings_snapshot()

    assert snapshot.source == "packaged_default"
    assert snapshot.credential_configured
    assert all(not item.writable for item in snapshot.values)
    assert all("api_key" not in item.key for item in snapshot.values)
    assert all(item.value != "lm-studio" for item in snapshot.values)
