from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = (
    "brain.audio",
    "brain.rag",
    "brain.memory",
    "brain.providers",
    "brain.runtime",
    "numpy",
    "torch",
)


def test_qt_and_presentation_modules_do_not_import_deep_backend() -> None:
    ui_root = Path(__file__).parents[2] / "brain" / "ui"
    presentation_files = (
        ui_root / "app.py",
        ui_root / "main_window.py",
        ui_root / "presentation.py",
        ui_root / "presentation_state.py",
        ui_root / "presentation_store.py",
        ui_root / "session_persistence.py",
        ui_root / "state.py",
        ui_root / "worker_binding.py",
        ui_root / "workers.py",
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
