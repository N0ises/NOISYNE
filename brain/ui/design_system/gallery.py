"""Small internal gallery used to exercise Sprint 3 primitives in the shell."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from .components import (
    ButtonVariant,
    Card,
    CheckBox,
    ComboBox,
    DesignButton,
    EmptyState,
    MetricCard,
    ProgressIndicator,
    StatusBadge,
    TextInput,
    ToggleSwitch,
)
from .semantics import VisualState
from .tokens import DEFAULT_TOKENS, DesignTokens


class ComponentGallery(QScrollArea):
    """Non-product demo surface; it deliberately contains no feature behavior."""

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("internalComponentGallery")
        self.setAccessibleName("Design system component gallery")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing.lg)

        description = QLabel(
            "Internal foundation preview -- reusable controls only, not a product page."
        )
        description.setProperty("textRole", "muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addWidget(_controls_card(tokens))
        layout.addWidget(_status_card(tokens))
        layout.addWidget(
            MetricCard("Foundation", "Ready", "Temporary neutral tokens", tokens=tokens),
        )
        layout.addWidget(
            EmptyState(
                "Empty state",
                "Later pages can supply data and intent without owning backend lifecycle.",
                tokens=tokens,
            ),
        )
        layout.addStretch(1)
        self.setWidget(content)


def _controls_card(tokens: DesignTokens) -> Card:
    card = Card("Controls", tokens=tokens)
    card.content_layout.addWidget(TextInput("Audio file", accessible_name="Audio file"))
    card.content_layout.addWidget(ComboBox(("Neutral option", "Alternate option")))
    card.content_layout.addWidget(CheckBox("Include optional detail"))
    card.content_layout.addWidget(ToggleSwitch("Optional capability"))
    card.content_layout.addWidget(
        DesignButton("Primary action", variant=ButtonVariant.PRIMARY, tokens=tokens)
    )
    return card


def _status_card(tokens: DesignTokens) -> Card:
    card = Card("Semantic states", tokens=tokens)
    for state in (
        VisualState.READY,
        VisualState.LOADING,
        VisualState.WARNING,
        VisualState.ERROR,
        VisualState.UNAVAILABLE,
    ):
        card.content_layout.addWidget(StatusBadge(state.value.title(), state))
    card.content_layout.addWidget(ProgressIndicator(None))
    return card
