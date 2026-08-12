from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QLabel, QPushButton, QTabWidget

from brain.ui.contracts import (
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    IntelligenceEvidence,
    IntelligenceItem,
    IntelligenceParameter,
    IntelligenceSnapshot,
    ReferenceFinding,
    ReferenceViewResult,
)
from brain.ui.intelligence_page import IntelligencePage
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    PageId,
    PresentationState,
    RuntimePresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore


def _capability(
    capability_id: str,
    availability: Availability,
    lifecycle: CapabilityLifecycle = CapabilityLifecycle.PRODUCTION,
) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        capability_id,
        capability_id,
        lifecycle,
        availability,
        reason=f"{capability_id} reason",
    )


def _analysis(tmp_path, *, warnings=()) -> AnalysisViewResult:
    engineering = IntelligenceItem(
        observation="Upper-mid energy is elevated.",
        finding="Harsh upper mids",
        explanations=("Dense guitars overlap the vocal presence range.",),
        recommendation="Review the upper-mid balance.",
        confidence=0.8125,
        evidence=(IntelligenceEvidence("severity", "medium"),),
    )
    mix = IntelligenceItem(
        observation="Dynamics are constrained.",
        finding="Limited crest range",
        recommendation="Review limiter gain reduction.",
        confidence=0.78,
    )
    plugin_with_parameters = IntelligenceItem(
        observation="Upper-mid prominence",
        finding="equalizer",
        explanations=("Dense guitars",),
        recommendation="Consider a parametric equalizer.",
        proposed_action="Evaluate an equalizer adjustment.",
        confidence=0.77,
        parameters=(
            IntelligenceParameter(
                "gain",
                -1.25,
                unit="dB",
                confidence=0.76,
                reason="Reduce prominence.",
            ),
        ),
    )
    plugin_without_parameters = IntelligenceItem(
        finding="compressor",
        recommendation="Consider gentle compression.",
    )
    return AnalysisViewResult(
        tmp_path / "mix.wav",
        "degraded" if warnings else "ok",
        "full_mix",
        84.0,
        "",
        warnings=warnings,
        intelligence=IntelligenceSnapshot(
            engineering=(engineering,),
            mix=(mix,),
            plugin=(plugin_with_parameters, plugin_without_parameters),
            reasoning="Provider-returned reasoning text.",
        ),
    )


def _state(tmp_path, *, warnings=()) -> PresentationState:
    analysis = _analysis(tmp_path, warnings=warnings)
    reference = ReferenceViewResult(
        Path("current.wav"),
        (Path("reference.wav"),),
        "ok",
        88.0,
        0.9,
        findings=(
            ReferenceFinding(
                "Reference balance",
                "Current low band differs.",
                "frequency",
                "medium",
                0.71,
                "Review low-band balance.",
                "technical_issue",
            ),
        ),
    )
    capabilities = (
        _capability(
            "engineering_analysis",
            Availability.AVAILABLE,
            CapabilityLifecycle.PLANNED,
        ),
        _capability("mix_intelligence", Availability.DEGRADED),
        _capability("plugin_intelligence", Availability.UNKNOWN),
        _capability("llm_reasoning", Availability.UNAVAILABLE),
    )
    return PresentationState(
        runtime=RuntimePresentationState(capabilities=capabilities),
        session=SessionState(
            last_analysis_result=analysis,
            last_reference_result=reference,
        ),
    )


def test_four_intelligence_sections_render_only_contract_data(qtbot, tmp_path) -> None:
    page = IntelligencePage()
    qtbot.addWidget(page)

    page.render(_state(tmp_path))

    tabs = page.findChild(QTabWidget, "intelligenceTabs")
    assert tabs.count() == 4
    assert [tabs.tabText(index) for index in range(4)] == [
        "Engineering Intelligence",
        "Mix Intelligence",
        "Plugin Intelligence",
        "AI Reasoning",
    ]
    texts = {label.objectName(): label.text() for label in page.findChildren(QLabel)}
    assert "Observation\nUpper-mid energy is elevated." in texts.values()
    assert "Finding\nHarsh upper mids" in texts.values()
    assert any("Cause / explanation\nDense guitars" in text for text in texts.values())
    assert "Recommendation\nReview the upper-mid balance." in texts.values()
    assert "Proposed action (display only)\nEvaluate an equalizer adjustment." in texts.values()
    assert "Confidence (raw)\n0.8125" in texts.values()
    assert all("%" not in text for text in texts.values())
    assert any("Reference balance" in label.text() for label in page.findChildren(QLabel))


def test_plugin_parameters_are_present_only_when_returned_and_actions_do_not_execute(
    qtbot, tmp_path
) -> None:
    page = IntelligencePage()
    qtbot.addWidget(page)
    state = _state(tmp_path)

    page.render(state)

    parameter_labels = page.findChildren(QLabel, "intelligenceParameters")
    assert len(parameter_labels) == 1
    assert "gain: -1.25 dB" in parameter_labels[0].text()
    assert "confidence (raw): 0.76" in parameter_labels[0].text()
    assert not any(
        button.text().casefold().startswith("apply") for button in page.findChildren(QPushButton)
    )
    assert state.session.last_analysis_result.intelligence.plugin[0].proposed_action == (
        "Evaluate an equalizer adjustment."
    )


def test_capability_and_provider_failure_preserve_deterministic_intelligence(
    qtbot, tmp_path
) -> None:
    page = IntelligencePage()
    qtbot.addWidget(page)
    state = _state(tmp_path, warnings=("Reasoning provider unavailable.",))
    analysis = state.session.last_analysis_result
    state = replace(
        state,
        session=replace(
            state.session,
            last_analysis_result=replace(
                analysis,
                intelligence=replace(analysis.intelligence, reasoning=""),
            ),
        ),
    )

    page.render(state)

    assert page.warning_card.isVisible() or not page.isVisible()
    assert "Reasoning provider unavailable." in page.warning_text.text()
    assert page.findChild(QLabel, "intelligenceFinding") is not None
    assert page.findChild(QLabel, "reasoningEmptyState") is not None
    badges = [label.text() for label in page.findChildren(QLabel)]
    assert "Unavailable" in badges
    assert "Degraded" in badges
    assert "Unknown" in badges
    assert "Planned" in badges


def test_empty_workspace_and_navigation_retention(qtbot, tmp_path) -> None:
    empty_page = IntelligencePage()
    qtbot.addWidget(empty_page)
    empty_page.render(PresentationState())
    assert empty_page.source_label.text() == "No retained analysis result."
    assert empty_page.findChild(QLabel, "engineeringEmptyState") is not None

    state = _state(tmp_path)
    store = PresentationStore(state)
    host = PageHost()
    qtbot.addWidget(host)
    intelligence = host.page(PageId.INTELLIGENCE)
    assert isinstance(intelligence, IntelligencePage)
    host.render(store.state)
    store.navigate(PageId.OVERVIEW)
    host.show_page(PageId.OVERVIEW)
    store.navigate(PageId.INTELLIGENCE)
    host.show_page(PageId.INTELLIGENCE)
    host.render(store.state)

    assert host.page(PageId.INTELLIGENCE) is intelligence
    assert store.state.session.last_analysis_result is state.session.last_analysis_result
    assert intelligence.findChild(QLabel, "intelligenceFinding") is not None
