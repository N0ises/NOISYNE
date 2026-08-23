from __future__ import annotations

import ast
from pathlib import Path

DEEP_BACKEND_PREFIXES = (
    "phasenox.audio",
    "phasenox.rag",
    "phasenox.memory",
    "phasenox.reference",
    "phasenox.report",
    "phasenox.providers",
    "phasenox.runtime",
    "phasenox.services",
    "torch",
    "transformers",
    "onnxruntime",
    "chromadb",
)


def test_qt_and_presentation_layers_do_not_import_deep_backend() -> None:
    ui_root = Path(__file__).parents[2] / "phasenox" / "ui"
    violations: list[str] = []
    for path in sorted(ui_root.rglob("*.py")):
        if "adapters" in path.parts or path.name == "job_gateway.py":
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
                if name.startswith(DEEP_BACKEND_PREFIXES)
            )

    assert violations == []


def test_only_adapter_and_gateway_may_import_application_backend() -> None:
    ui_root = Path(__file__).parents[2] / "phasenox" / "ui"
    violations: list[str] = []
    for path in sorted(ui_root.rglob("*.py")):
        if "adapters" in path.parts or path.name == "job_gateway.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "phasenox.application" in source:
            violations.append(str(path.relative_to(ui_root)))

    assert violations == []
