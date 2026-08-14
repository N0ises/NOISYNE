from __future__ import annotations

import json
from pathlib import Path

import pytest

from noisyne.audio.mix.models import MixIntelligenceResult, ProcessingStep
from noisyne.audio.plugin.models import (
    ParameterRecommendation,
    PluginIntelligenceResult,
    PluginIntelligenceStep,
    ProcessingGoal,
)
from noisyne.integration import (
    AbletonAdapter,
    AdapterFactory,
    CubaseAdapter,
    ExportRequest,
    FLStudioAdapter,
    ReaperAdapter,
    StudioOneAdapter,
    WorkflowSession,
)
from noisyne.report.models import ReportIssue, SoundBrainReport


@pytest.fixture
def tmp_export_dir(tmp_path: Path) -> Path:
    return tmp_path / "exports"


@pytest.fixture
def mock_report() -> SoundBrainReport:
    return SoundBrainReport(
        audio_type="full_mix",
        source_type="file",
        instrument=None,
        is_full_mix=True,
        confidence=0.92,
        score=78.0,
        strengths=["clear mids"],
        issues=[
            ReportIssue(
                title="harsh highs",
                severity="medium",
                description="2-5 kHz energy is elevated",
                recommendation="gentle EQ cut",
            ),
        ],
        recommendations=["reduce 3 kHz"],
        ai_summary="summary",
    )


@pytest.fixture
def mock_mix_intelligence() -> MixIntelligenceResult:
    return MixIntelligenceResult(
        processing_chain=[
            ProcessingStep(
                order=1,
                target="frequency_balance",
                plugin_type="EQ",
                suggestion="reduce 2-5 kHz",
                estimated_impact="high",
                confidence=0.85,
            ),
        ],
    )


@pytest.fixture
def mock_plugin_intelligence() -> PluginIntelligenceResult:
    goal = ProcessingGoal(
        id="g1",
        description="smooth highs",
        target="frequency_balance",
        root_cause="harsh highs",
        action="EQ cut",
        confidence=0.85,
    )
    return PluginIntelligenceResult(
        goals=[goal],
        steps=[
            PluginIntelligenceStep(
                order=1,
                goal=goal,
                plugin_category="EQ",
                plugin_type="parametric_eq",
                parameter_recommendations=[
                    ParameterRecommendation(
                        name="frequency",
                        value=3000,
                        unit="Hz",
                        confidence=0.9,
                    ),
                ],
                suggestion="cut 3 kHz",
                estimated_impact="high",
                confidence=0.85,
            ),
        ],
    )


@pytest.fixture
def export_request(
    tmp_export_dir: Path,
    mock_report: SoundBrainReport,
    mock_mix_intelligence: MixIntelligenceResult,
    mock_plugin_intelligence: PluginIntelligenceResult,
) -> ExportRequest:
    return ExportRequest(
        session=WorkflowSession(
            daw_name="ableton",
            project_name="test_project",
            sample_rate=44100,
            bpm=120.0,
            time_signature="4/4",
        ),
        output_dir=tmp_export_dir,
        report=mock_report,
        mix_intelligence=mock_mix_intelligence,
        plugin_intelligence=mock_plugin_intelligence,
    )


@pytest.mark.parametrize(
    "name",
    ["ableton", "reaper", "cubase", "flstudio", "studio_one"],
)
def test_adapter_capabilities_are_non_empty(name: str):
    adapter = AdapterFactory.get(name)
    assert adapter is not None
    caps = adapter.capabilities()
    assert len(caps) >= 4
    names = {cap.name for cap in caps}
    assert "report_export" in names
    assert "processing_chain" in names


@pytest.mark.parametrize(
    "adapter_class",
    [AbletonAdapter, ReaperAdapter, CubaseAdapter, FLStudioAdapter, StudioOneAdapter],
)
def test_export_analysis_creates_json(
    adapter_class: type,
    export_request: ExportRequest,
):
    adapter = adapter_class()
    result = adapter.export_analysis(export_request)
    assert result.success
    assert result.adapter_name == adapter.name
    assert len(result.files) == 1
    assert result.files[0].exists()
    assert result.files[0].suffix == ".json"
    data = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert data["adapter"] == adapter.name
    assert data["analysis"]["score"] == 78.0


@pytest.mark.parametrize(
    "adapter_class",
    [AbletonAdapter, ReaperAdapter, CubaseAdapter, FLStudioAdapter, StudioOneAdapter],
)
def test_export_processing_chain_creates_json_and_text(
    adapter_class: type,
    export_request: ExportRequest,
):
    adapter = adapter_class()
    result = adapter.export_processing_chain(export_request)
    assert result.success
    assert len(result.files) == 2
    json_file = next(f for f in result.files if f.suffix == ".json")
    text_file = next(f for f in result.files if f.suffix == ".txt")
    assert json_file.exists()
    assert text_file.exists()
    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert data["processing_chain"]
    assert data["processing_chain"][0]["target"] == "frequency_balance"


@pytest.mark.parametrize(
    "adapter_class",
    [AbletonAdapter, ReaperAdapter, CubaseAdapter, FLStudioAdapter, StudioOneAdapter],
)
def test_export_plugin_recommendations_creates_json(
    adapter_class: type,
    export_request: ExportRequest,
):
    adapter = adapter_class()
    result = adapter.export_plugin_recommendations(export_request)
    assert result.success
    assert len(result.files) == 1
    data = json.loads(result.files[0].read_text(encoding="utf-8"))
    assert data["plugin_recommendations"]
    assert data["plugin_recommendations"][0]["plugin_category"] == "EQ"


@pytest.mark.parametrize(
    "adapter_class",
    [AbletonAdapter, ReaperAdapter, CubaseAdapter, FLStudioAdapter, StudioOneAdapter],
)
def test_export_report_creates_json_and_markdown(
    adapter_class: type,
    export_request: ExportRequest,
):
    adapter = adapter_class()
    result = adapter.export_report(export_request)
    assert result.success
    assert len(result.files) == 2
    json_file = next(f for f in result.files if f.suffix == ".json")
    md_file = next(f for f in result.files if f.suffix == ".md")
    assert json_file.exists()
    assert md_file.exists()


def test_empty_request_exports_without_crashing(tmp_export_dir: Path):
    request = ExportRequest(
        session=WorkflowSession(daw_name="reaper"),
        output_dir=tmp_export_dir,
    )
    adapter = ReaperAdapter()
    for method_name in (
        "export_analysis",
        "export_processing_chain",
        "export_plugin_recommendations",
        "export_report",
    ):
        result = getattr(adapter, method_name)(request)
        assert result.success
        assert result.files
        for file in result.files:
            assert file.exists()


def test_no_daw_communication_occurs(export_request: ExportRequest):
    """Adapters are pure contracts and must not spawn processes or open sockets."""
    adapter = AbletonAdapter()
    for method_name in (
        "export_analysis",
        "export_processing_chain",
        "export_plugin_recommendations",
        "export_report",
    ):
        result = getattr(adapter, method_name)(export_request)
        for note in result.notes:
            assert "No DAW communication occurred" in note
