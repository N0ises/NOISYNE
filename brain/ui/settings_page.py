"""Read-only V1 Settings & Runtime workspace backed by stable UI contracts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .contracts import SettingValue
from .design_system.components import ButtonVariant, Card, DesignButton, PageHeader, StatusBadge
from .design_system.semantics import VisualState
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import (
    PageId,
    PresentationState,
    RuntimePresentationPhase,
    SettingsPresentationPhase,
)

_CATEGORY_ORDER = (
    "provider",
    "models",
    "runtime",
    "audio",
    "knowledge",
    "reports",
    "storage",
    "logging",
)
_CATEGORY_LABELS = {
    "provider": "AI Provider",
    "models": "Models",
    "runtime": "Runtime",
    "audio": "Audio Defaults",
    "knowledge": "Knowledge / RAG",
    "reports": "Reports",
    "storage": "Storage / Cache",
    "logging": "Logging",
    "application": "Application",
}


class SettingsPage(QScrollArea):
    refresh_settings_requested = Signal()
    refresh_runtime_requested = Signal()
    page_id = PageId.SETTINGS

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-settings")
        self.setAccessibleName("Settings and Runtime page")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._tokens = tokens
        self._settings_signature: tuple = ()

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(
            PageHeader(
                "Settings & Runtime",
                "Inspect effective V1 configuration separately from current runtime availability.",
                tokens=tokens,
            )
        )

        policy_card = Card("Configuration policy", tokens=tokens)
        self.policy_badge = StatusBadge("Read-only", VisualState.IDLE)
        self.policy_message = QLabel(
            "V1 loads packaged defaults at process start and has no validated user-settings "
            "persistence contract. Settings cannot be edited from Desktop."
        )
        self.policy_message.setObjectName("settingsPolicy")
        self.policy_message.setWordWrap(True)
        policy_card.content_layout.addWidget(self.policy_badge, 0, Qt.AlignmentFlag.AlignLeft)
        policy_card.content_layout.addWidget(self.policy_message)
        layout.addWidget(policy_card)

        runtime_card = Card("Runtime status", tokens=tokens)
        self.runtime_badge = StatusBadge("Unknown", VisualState.IDLE)
        self.runtime_summary = QLabel("Runtime status has not been loaded.")
        self.runtime_summary.setObjectName("settingsRuntimeSummary")
        self.runtime_summary.setWordWrap(True)
        self.provider_summary = QLabel("Provider availability has not been loaded.")
        self.provider_summary.setObjectName("settingsProviderStatus")
        self.provider_summary.setWordWrap(True)
        runtime_actions = QHBoxLayout()
        self.refresh_runtime_button = DesignButton(
            "Refresh runtime status", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.reload_settings_button = DesignButton("Reload configuration", tokens=tokens)
        runtime_actions.addWidget(self.refresh_runtime_button)
        runtime_actions.addWidget(self.reload_settings_button)
        runtime_actions.addStretch(1)
        runtime_card.content_layout.addWidget(self.runtime_badge, 0, Qt.AlignmentFlag.AlignLeft)
        runtime_card.content_layout.addWidget(self.runtime_summary)
        runtime_card.content_layout.addWidget(self.provider_summary)
        runtime_card.content_layout.addLayout(runtime_actions)
        layout.addWidget(runtime_card)

        settings_card = Card("Effective configuration", tokens=tokens)
        self.settings_status = QLabel("Loading effective configuration…")
        self.settings_status.setObjectName("settingsStatus")
        self.settings_status.setWordWrap(True)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("settingsCategories")
        settings_card.content_layout.addWidget(self.settings_status)
        settings_card.content_layout.addWidget(self.tabs)
        layout.addWidget(settings_card)
        layout.addStretch(1)
        self.setWidget(content)

        self.refresh_runtime_button.clicked.connect(self.refresh_runtime_requested)
        self.reload_settings_button.clicked.connect(self.refresh_settings_requested)

    def render(self, state: PresentationState) -> None:
        settings_state = state.settings
        if settings_state.phase is SettingsPresentationPhase.LOADING:
            self.settings_status.setText("Loading effective configuration…")
        elif settings_state.phase is SettingsPresentationPhase.FAILURE:
            self.settings_status.setText(
                settings_state.error.user_message
                if settings_state.error
                else "Effective configuration could not be loaded."
            )
        elif settings_state.snapshot is not None:
            snapshot = settings_state.snapshot
            self.settings_status.setText(
                f"Source: {snapshot.source} | Revision: {snapshot.revision} | "
                f"Credential configured: {'Yes' if snapshot.credential_configured else 'No'}"
            )
            self._render_settings(snapshot.values)

        runtime = state.runtime
        visual = {
            RuntimePresentationPhase.LOADING: VisualState.RUNNING,
            RuntimePresentationPhase.READY: VisualState.SUCCESS,
            RuntimePresentationPhase.DEGRADED: VisualState.WARNING,
            RuntimePresentationPhase.UNAVAILABLE: VisualState.UNAVAILABLE,
            RuntimePresentationPhase.UNKNOWN: VisualState.IDLE,
        }[runtime.phase]
        self.runtime_badge.setText(runtime.phase.value.title())
        self.runtime_badge.set_state(visual)
        self.refresh_runtime_button.setEnabled(
            runtime.phase is not RuntimePresentationPhase.LOADING
        )
        if runtime.status is None:
            self.runtime_summary.setText("Runtime status is unknown.")
            self.provider_summary.setText("Provider availability is unknown.")
        else:
            status = runtime.status
            path_lines = [
                f"{item.kind}: "
                f"{'exists' if item.exists else 'missing'}, "
                f"{'readable' if item.readable else 'not readable'}, "
                f"{'writable' if item.writable else 'not writable'}"
                for item in status.paths
            ]
            loaded_models = ", ".join(item.name for item in status.loaded_models)
            self.runtime_summary.setText(
                f"Configured request: {status.requested_device}\n"
                f"Effective device: {status.effective_device or 'Unknown'}\n"
                f"Runtime state: {status.state.value}\n"
                f"Reason: {status.device_reason or 'No reason supplied.'}\n"
                f"Configuration source: {status.configuration_source}\n"
                f"Status checked: {status.checked_at.isoformat()}\n"
                f"Loaded models reported: {loaded_models or 'None'}"
                + ("\nPaths:\n" + "\n".join(path_lines) if path_lines else "")
            )
            provider = status.provider
            self.provider_summary.setText(
                f"Provider runtime: {provider.name}\n"
                f"Availability: {provider.availability.value}\n"
                f"Reason: {provider.reason or 'No reason supplied.'}"
            )

    def _render_settings(self, values: tuple[SettingValue, ...]) -> None:
        signature = tuple(
            (
                item.key,
                item.value,
                item.writable,
                item.restart_required,
                item.category,
                item.display_name,
                item.read_only_reason,
            )
            for item in values
        )
        if signature == self._settings_signature:
            return
        current_tab = self.tabs.currentIndex()
        self._settings_signature = signature
        self.tabs.clear()
        categories = tuple(
            category
            for category in (*_CATEGORY_ORDER, "application")
            if any(item.category == category for item in values)
        )
        for category in categories:
            page = QWidget()
            form = QFormLayout(page)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            for item in values:
                if item.category != category:
                    continue
                label = QLabel(self._display_value(item.value))
                label.setObjectName(f"setting-{item.key}")
                label.setAccessibleName(item.display_name or item.key)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                label.setWordWrap(True)
                reason = item.read_only_reason or ""
                mode = "Editable" if item.writable else "Read-only"
                restart = " | Restart required" if item.restart_required else ""
                label.setToolTip(f"{mode}{restart}. {reason}".strip())
                field = QWidget()
                field_layout = QVBoxLayout(field)
                field_layout.setContentsMargins(0, 0, 0, 0)
                field_layout.setSpacing(self._tokens.spacing.xs)
                field_layout.addWidget(label)
                truth = QLabel(f"{mode}{restart}")
                truth.setObjectName(f"setting-mode-{item.key}")
                truth.setProperty("muted", True)
                field_layout.addWidget(truth)
                form.addRow(item.display_name or item.key, field)
            self.tabs.addTab(page, _CATEGORY_LABELS.get(category, category.title()))
        if self.tabs.count():
            self.tabs.setCurrentIndex(min(max(current_tab, 0), self.tabs.count() - 1))

    @staticmethod
    def _display_value(value: str | float | bool) -> str:
        if isinstance(value, bool):
            return "Enabled" if value else "Disabled"
        return str(value)
