"""Persistent Intelligence workspace for retained stable UI DTOs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from .contracts import CapabilityLifecycle, IntelligenceItem, ReferenceFinding
from .design_system.components import Card, PageHeader, StatusBadge, TabView
from .design_system.semantics import VisualState, availability_visual_state
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .intelligence_presentation import (
    IntelligenceCapabilityState,
    build_intelligence_workspace,
)
from .presentation_state import PageId, PresentationState
from .result_presentation import raw_value_text


class IntelligencePage(QScrollArea):
    page_id = PageId.INTELLIGENCE

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-intelligence")
        self.setAccessibleName("Intelligence workspace")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tokens = tokens
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(
            tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl
        )
        self._layout.setSpacing(tokens.spacing.lg)
        self._layout.addWidget(
            PageHeader(
                "Intelligence",
                "Retained observations, findings, explanations, and recommendations.",
                tokens=tokens,
            )
        )
        self.source_label = QLabel("No retained analysis result.")
        self.source_label.setObjectName("intelligenceSource")
        self.source_label.setWordWrap(True)
        self._layout.addWidget(self.source_label)
        self.warning_card = Card("Analysis warnings", tokens=tokens)
        self.warning_card.setObjectName("intelligenceWarnings")
        self.warning_text = QLabel()
        self.warning_text.setWordWrap(True)
        self.warning_card.content_layout.addWidget(self.warning_text)
        self._layout.addWidget(self.warning_card)
        self.tabs = TabView(accessible_name="Intelligence sections")
        self.tabs.setObjectName("intelligenceTabs")
        self._layout.addWidget(self.tabs, 1)
        self.setWidget(content)
        self.render(PresentationState())

    def render(self, state: PresentationState) -> None:
        workspace = build_intelligence_workspace(state)
        self.source_label.setText(
            f"Retained analysis: {workspace.source_path}"
            if workspace.source_path
            else "No retained analysis result."
        )
        self.warning_card.setVisible(bool(workspace.warnings))
        self.warning_text.setText("\n".join(workspace.warnings))
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()
        self.tabs.addTab(
            self._section(
                "engineering",
                workspace.capability("engineering"),
                workspace.engineering,
                reference_findings=workspace.reference_findings,
            ),
            "Engineering Intelligence",
        )
        self.tabs.addTab(
            self._section("mix", workspace.capability("mix"), workspace.mix),
            "Mix Intelligence",
        )
        self.tabs.addTab(
            self._section("plugin", workspace.capability("plugin"), workspace.plugin),
            "Plugin Intelligence",
        )
        self.tabs.addTab(
            self._reasoning_section(workspace.capability("reasoning"), workspace.reasoning),
            "AI Reasoning",
        )

    def _section(
        self,
        section: str,
        capability: IntelligenceCapabilityState,
        items: tuple[IntelligenceItem, ...],
        *,
        reference_findings: tuple[ReferenceFinding, ...] = (),
    ) -> QWidget:
        content, layout = self._scroll_content(section)
        self._add_capability(layout, capability)
        for index, item in enumerate(items):
            layout.addWidget(self._item_card(item, f"{section}Item{index}"))
        if reference_findings:
            reference_title = QLabel("Reference findings")
            reference_title.setProperty("textRole", "title")
            layout.addWidget(reference_title)
            for finding in reference_findings:
                layout.addWidget(self._reference_finding_card(finding))
        if not items and not reference_findings:
            empty = QLabel(f"No retained {section} intelligence was returned.")
            empty.setObjectName(f"{section}EmptyState")
            empty.setWordWrap(True)
            layout.addWidget(empty)
        layout.addStretch(1)
        return content

    def _reasoning_section(
        self, capability: IntelligenceCapabilityState, reasoning: str
    ) -> QWidget:
        content, layout = self._scroll_content("reasoning")
        self._add_capability(layout, capability)
        if reasoning:
            card = Card("AI reasoning / interpretation", tokens=self._tokens)
            card.setProperty("semantic", "intelligence")
            text = QLabel(reasoning)
            text.setObjectName("reasoningText")
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.content_layout.addWidget(text)
            layout.addWidget(card)
        else:
            empty = QLabel("No retained AI reasoning was returned.")
            empty.setObjectName("reasoningEmptyState")
            empty.setWordWrap(True)
            layout.addWidget(empty)
        layout.addStretch(1)
        return content

    def _scroll_content(self, name: str) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName(f"{name}IntelligenceSection")
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            self._tokens.spacing.md,
            self._tokens.spacing.md,
            self._tokens.spacing.md,
            self._tokens.spacing.md,
        )
        layout.setSpacing(self._tokens.spacing.md)
        scroll.setWidget(content)
        return scroll, layout

    def _add_capability(self, layout: QVBoxLayout, capability: IntelligenceCapabilityState) -> None:
        card = Card("Capability status", tokens=self._tokens)
        planned = capability.lifecycle is CapabilityLifecycle.PLANNED
        badge = StatusBadge(
            "Planned" if planned else capability.availability.value.title(),
            VisualState.DISABLED if planned else availability_visual_state(capability.availability),
        )
        lifecycle = capability.lifecycle.value if capability.lifecycle else "unknown"
        detail = QLabel(f"Lifecycle: {lifecycle}\n{capability.reason}")
        detail.setWordWrap(True)
        card.content_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        card.content_layout.addWidget(detail)
        layout.addWidget(card)

    def _item_card(self, item: IntelligenceItem, object_name: str) -> Card:
        card = Card(tokens=self._tokens)
        card.setObjectName(object_name)
        self._add_field(card, "Observation", item.observation, "intelligenceObservation")
        self._add_field(card, "Finding", item.finding, "intelligenceFinding")
        if item.explanations:
            self._add_field(
                card,
                "Cause / explanation",
                "\n".join(item.explanations),
                "intelligenceExplanation",
            )
        self._add_field(
            card,
            "Recommendation",
            item.recommendation,
            "intelligenceRecommendation",
        )
        self._add_field(
            card,
            "Proposed action (display only)",
            item.proposed_action,
            "intelligenceProposedAction",
        )
        if item.confidence is not None:
            self._add_field(
                card,
                "Confidence (raw)",
                raw_value_text(item.confidence),
                "intelligenceConfidence",
            )
        if item.evidence:
            evidence = "\n".join(
                f"{entry.label}: {raw_value_text(entry.value)}" for entry in item.evidence
            )
            self._add_field(card, "Evidence / context", evidence, "intelligenceEvidence")
        if item.parameters:
            parameter_lines = []
            for parameter in item.parameters:
                line = f"{parameter.name}: {raw_value_text(parameter.value)}"
                if parameter.unit is not None:
                    line += f" {parameter.unit}"
                if parameter.confidence is not None:
                    line += f"; confidence (raw): {raw_value_text(parameter.confidence)}"
                if parameter.reason:
                    line += f"; reason: {parameter.reason}"
                if parameter.range_min is not None:
                    line += f"; range min: {raw_value_text(parameter.range_min)}"
                if parameter.range_max is not None:
                    line += f"; range max: {raw_value_text(parameter.range_max)}"
                parameter_lines.append(line)
            self._add_field(
                card,
                "Backend-provided parameters",
                "\n".join(parameter_lines),
                "intelligenceParameters",
            )
        return card

    def _reference_finding_card(self, finding: ReferenceFinding) -> Card:
        card = Card(finding.title, tokens=self._tokens)
        self._add_field(card, "Finding", finding.description, "referenceIntelligenceFinding")
        self._add_field(
            card,
            "Recommendation",
            finding.recommendation,
            "referenceIntelligenceRecommendation",
        )
        evidence = (
            f"category: {finding.category}\nseverity: {finding.severity}\n"
            f"confidence (raw): {raw_value_text(finding.confidence)}"
        )
        self._add_field(card, "Evidence / context", evidence, "referenceIntelligenceEvidence")
        return card

    @staticmethod
    def _add_field(card: Card, title: str, value: str, object_name: str) -> None:
        if not value:
            return
        label = QLabel(f"{title}\n{value}")
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card.content_layout.addWidget(label)
