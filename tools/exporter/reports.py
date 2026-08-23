"""Human-readable export and diagnostic report builders."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .analyzer import SourceAnalysis
from .scanner import FileRecord


LINE = "=" * 70


def document_header(title: str, generated_at: str) -> str:
    return f"{LINE}\n{title}\n{LINE}\n\nGenerated\n\n{generated_at}\n\nChatGPT Export V2\n\n"


def module_document(
    name: str,
    records: list[FileRecord],
    analyses: dict[Path, SourceAnalysis],
    generated_at: str,
) -> str:
    lines = [document_header("MODULE", generated_at), name, ""]
    internal_imports: set[str] = set()
    external_imports: set[str] = set()
    class_count = function_count = line_count = 0
    for record in records:
        lines.extend([LINE, "FILE", "", record.relative_path.as_posix(), "", LINE, ""])
        lines.append(record.content.rstrip("\n") if record.content is not None else f"[Content skipped: {record.skipped_reason}]")
        analysis = analyses.get(record.relative_path)
        if analysis:
            class_count += len(analysis.classes)
            function_count += len(analysis.functions)
            line_count += analysis.lines
            for imported in analysis.imports:
                (internal_imports if imported.startswith(".") or imported.startswith("phasenox.") else external_imports).add(imported)
    lines.extend([
        "", LINE, "", "SUMMARY", "", f"Files : {len(records)}", f"Classes : {class_count}",
        f"Functions : {function_count}", f"Imports : {len(internal_imports | external_imports)}",
        f"Lines : {line_count}", "", LINE,
    ])
    return "\n".join(lines)


def requirements_document(records: list[FileRecord], external_imports: set[str], generated_at: str) -> str:
    requirements = [record for record in records if record.relative_path.name.lower().startswith("requirements")]
    lines = [document_header("REQUIREMENTS", generated_at)]
    if requirements:
        for record in requirements:
            lines.extend([f"# {record.relative_path.as_posix()}", record.content or "[Unreadable]", ""])
    else:
        lines.extend(sorted(external_imports) or ["No external Python imports detected."])
    return "\n".join(lines) + "\n"


def import_graph_document(graph: dict[str, list[str]], generated_at: str) -> str:
    lines = [document_header("IMPORT GRAPH", generated_at)]
    for module, imports in sorted(graph.items()):
        lines.append(module)
        lines.extend(f"  ↓ {dependency}" for dependency in imports)
        lines.append("")
    return "\n".join(lines)


def unused_files_document(analyses: dict[Path, SourceAnalysis], graph: dict[str, list[str]], generated_at: str) -> str:
    referenced = {dependency for dependencies in graph.values() for dependency in dependencies}
    unused = [module for module in graph if module not in referenced and not module.endswith(".__init__")]
    return document_header("UNUSED FILES", generated_at) + "\n".join(sorted(unused) or ["No unreferenced Python modules found."]) + "\n"


def duplicate_names_document(duplicates: dict[str, list[str]], generated_at: str) -> str:
    lines = [document_header("DUPLICATE SYMBOLS", generated_at)]
    if not duplicates:
        lines.append("No duplicate symbols found.")
    for symbol, paths in sorted(duplicates.items()):
        lines.extend([symbol, *[f"  {path}" for path in paths], ""])
    return "\n".join(lines)


def cycles_document(cycles: list[list[str]], generated_at: str) -> str:
    lines = [document_header("CIRCULAR IMPORTS", generated_at)]
    if not cycles:
        lines.append("No circular imports found.")
    for cycle in cycles:
        lines.append("\n↓\n".join(cycle))
        lines.append("")
    return "\n".join(lines)
