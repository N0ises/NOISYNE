from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "brain.audio",
    "brain.rag",
    "brain.memory",
    "brain.reference",
    "brain.report",
    "brain.infrastructure.config",
    "brain.providers",
    "brain.runtime",
    "brain.services",
    "chromadb",
    "numpy",
    "torch",
    "transformers",
)


def test_qt_and_presentation_modules_do_not_import_deep_backend() -> None:
    ui_root = Path(__file__).parents[2] / "brain" / "ui"
    presentation_files = (
        ui_root / "app.py",
        ui_root / "analysis_controller.py",
        ui_root / "analyze_page.py",
        ui_root / "analyze_state.py",
        ui_root / "dashboard.py",
        ui_root / "main_window.py",
        ui_root / "presentation.py",
        ui_root / "presentation_state.py",
        ui_root / "presentation_store.py",
        ui_root / "result_presentation.py",
        ui_root / "result_view.py",
        ui_root / "reference_controller.py",
        ui_root / "reference_page.py",
        ui_root / "reference_result_view.py",
        ui_root / "reference_state.py",
        ui_root / "intelligence_page.py",
        ui_root / "intelligence_presentation.py",
        ui_root / "knowledge_controller.py",
        ui_root / "knowledge_page.py",
        ui_root / "knowledge_state.py",
        ui_root / "report_controller.py",
        ui_root / "reports_page.py",
        ui_root / "settings_controller.py",
        ui_root / "settings_page.py",
        ui_root / "pages.py",
        ui_root / "shell_surfaces.py",
        ui_root / "session_persistence.py",
        ui_root / "state.py",
        ui_root / "worker_binding.py",
        ui_root / "workers.py",
        *sorted((ui_root / "design_system").glob("*.py")),
    )

    violations = []
    for path in presentation_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            violations.extend(
                f"{path.name}: {name}" for name in names if name.startswith(FORBIDDEN_PREFIXES)
            )

    assert violations == []


def test_design_system_has_no_absolute_backend_imports() -> None:
    design_root = Path(__file__).parents[2] / "brain" / "ui" / "design_system"
    violations = []
    for path in design_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                level = 0
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
                level = node.level
            else:
                continue
            violations.extend(
                f"{path.name}: {name}"
                for name in names
                if level == 0 and name.startswith("brain.") and not name.startswith("brain.ui")
            )

    assert violations == []


def test_analyze_modules_do_not_import_adapter_or_v1_domain_implementations() -> None:
    ui_root = Path(__file__).parents[2] / "brain" / "ui"
    analyze_files = (
        ui_root / "analysis_controller.py",
        ui_root / "analyze_page.py",
        ui_root / "analyze_state.py",
        ui_root / "result_presentation.py",
        ui_root / "result_view.py",
        ui_root / "reference_controller.py",
        ui_root / "reference_page.py",
        ui_root / "reference_result_view.py",
        ui_root / "reference_state.py",
        ui_root / "intelligence_page.py",
        ui_root / "intelligence_presentation.py",
        ui_root / "knowledge_controller.py",
        ui_root / "knowledge_page.py",
        ui_root / "knowledge_state.py",
        ui_root / "report_controller.py",
        ui_root / "reports_page.py",
        ui_root / "settings_controller.py",
        ui_root / "settings_page.py",
    )
    forbidden = (*FORBIDDEN_PREFIXES, "brain.application", "brain.ui.adapters")
    violations = []
    for path in analyze_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            violations.extend(
                f"{path.name}: {name}" for name in names if name.startswith(forbidden)
            )

    assert violations == []


def test_dashboard_does_not_import_adapter_or_backend_implementations() -> None:
    dashboard = Path(__file__).parents[2] / "brain" / "ui" / "dashboard.py"
    tree = ast.parse(dashboard.read_text(encoding="utf-8"), filename=str(dashboard))
    forbidden = (*FORBIDDEN_PREFIXES, "brain.ui.adapters")
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        violations.extend(name for name in names if name.startswith(forbidden))

    assert violations == []


def test_every_non_adapter_ui_module_respects_desktop_application_boundary() -> None:
    """Keep this broad so newly added pages cannot silently bypass the adapter seam."""
    ui_root = Path(__file__).parents[2] / "brain" / "ui"
    forbidden = (
        *FORBIDDEN_PREFIXES,
        "brain.application",
        "brain.domain",
        "brain.processing",
    )
    violations = []
    for path in sorted(ui_root.rglob("*.py")):
        if "adapters" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            violations.extend(
                f"{path.relative_to(ui_root)}: {name}"
                for name in names
                if name.startswith(forbidden)
            )

    assert violations == []
