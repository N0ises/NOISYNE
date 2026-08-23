"""Command-line interface for Export V2."""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .analyzer import (
    analyze_records,
    api_manifest,
    build_import_graph,
    duplicate_symbols,
    find_cycles,
)
from .architecture import architecture_json, render_structure_tree
from .bundle import ExportBundle
from .config import DEFAULT_MAX_FILE_SIZE, ExportConfig
from .reports import (
    cycles_document,
    document_header,
    duplicate_names_document,
    import_graph_document,
    module_document,
    requirements_document,
    unused_files_document,
)
from .scanner import FileRecord, scan_project, scan_structure
from .statistics import statistics_json
from .utils import load_ignore_patterns


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a project into modular development-review files."
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("."),
        help="project directory (default: current directory)",
    )
    parser.add_argument(
        "--full", action="store_true", help="write all exports and reports (default action)"
    )
    parser.add_argument("--tree", action="store_true", help="write only the complete project tree")
    parser.add_argument(
        "--module", metavar="NAME", help="export only files matching one module or folder name"
    )
    parser.add_argument("--stats", action="store_true", help="write only statistics.json")
    parser.add_argument(
        "--architecture",
        action="store_true",
        help="write only architecture and import graph outputs",
    )
    parser.add_argument(
        "--changed", action="store_true", help="limit selected files to Git changes"
    )
    parser.add_argument(
        "--search", metavar="TEXT", help="limit selected files to readable files containing text"
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="exports directory (default: <project>/exports)"
    )
    parser.add_argument("--max-file-size", type=int, default=DEFAULT_MAX_FILE_SIZE, metavar="BYTES")
    parser.add_argument(
        "--extensions", nargs="+", help="only export these extensions, e.g. py js ts md"
    )
    parser.add_argument("--exclude-dir", action="append", default=[], metavar="NAME")
    parser.add_argument(
        "--ignore-file",
        type=Path,
        metavar="PATH",
        help="rules file (default: <project>/.exportignore)",
    )
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument("--tree-depth", type=int, metavar="LEVELS")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.path.resolve()
    if not root.is_dir():
        raise SystemExit(f"Error: project directory does not exist: {root}")
    if args.max_file_size < 0 or (args.tree_depth is not None and args.tree_depth < 0):
        raise SystemExit("Error: size and tree-depth values cannot be negative")

    output_dir = args.output_dir.resolve() if args.output_dir else root / "exports"
    ignore_file = args.ignore_file.resolve() if args.ignore_file else root / ".exportignore"
    excluded_directories = set(args.exclude_dir)
    if output_dir.parent == root:
        excluded_directories.add(output_dir.name)
    config = ExportConfig(
        root=root,
        output=output_dir / ".export-in-progress.txt",
        include_hidden=args.include_hidden,
        max_file_size=args.max_file_size,
        extensions=set(args.extensions) if args.extensions else None,
        excluded_directories=excluded_directories,
        ignore_patterns=load_ignore_patterns(ignore_file),
        tree_depth=args.tree_depth,
    )
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    bundle = ExportBundle(output_dir, root, generated_at)
    if args.tree:
        print(f"Scanning project structure: {root}", flush=True)
        structure = scan_structure(config)
        bundle.text(
            "tree.txt",
            document_header("PROJECT TREE", generated_at)
            + render_structure_tree(root, structure, config.tree_depth)
            + "\n",
        )
        _finish(bundle, output_dir)
        return 0

    print(f"Scanning: {root}", flush=True)
    records = scan_project(
        config, on_progress=lambda count: print(f"  Scanned {count:,} files...", flush=True)
    )
    records = _filter_records(records, root, args.changed, args.search)
    structure = (
        scan_structure(config) if not (args.module or args.stats or args.architecture) else []
    )
    print(f"Analyzing {len(records):,} selected files...", flush=True)
    analyses = analyze_records(records)

    if args.module:
        selected = _select_module(records, args.module)
        if not selected:
            raise SystemExit(f"No files matched module: {args.module}")
        _write_module(bundle, args.module, selected, analyses, generated_at)
        _finish(bundle, output_dir)
        return 0

    if args.stats:
        bundle.json("statistics.json", statistics_json(records, analyses, root.name, generated_at))
    elif args.architecture:
        _write_architecture(bundle, analyses, generated_at)
    else:
        _write_full(bundle, config, records, structure, analyses, root.name, generated_at)
    _finish(bundle, output_dir)
    return 0


def _filter_records(
    records: list[FileRecord], root: Path, changed: bool, search: str | None
) -> list[FileRecord]:
    changed_paths = _git_changed_paths(root) if changed else None
    needle = search.casefold() if search else None
    return [
        record
        for record in records
        if (changed_paths is None or record.relative_path.as_posix() in changed_paths)
        and (needle is None or (record.content is not None and needle in record.content.casefold()))
    ]


def _git_changed_paths(root: Path) -> set[str]:
    command = ["git", "-C", str(root), "status", "--porcelain"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Error: --changed requires a Git repository ({error})") from error
    return {line[3:].replace("\\", "/") for line in result.stdout.splitlines() if len(line) > 3}


def _select_module(records: list[FileRecord], selector: str) -> list[FileRecord]:
    needle = selector.casefold()
    return [
        record
        for record in records
        if any(needle in part.casefold() for part in record.relative_path.parts)
        or needle in record.relative_path.stem.casefold()
    ]


def _write_full(
    bundle: ExportBundle,
    config: ExportConfig,
    records: list[FileRecord],
    structure: list[tuple[Path, bool]],
    analyses: dict,
    project: str,
    generated_at: str,
) -> None:
    bundle.text(
        "tree.txt",
        document_header("PROJECT TREE", generated_at)
        + render_structure_tree(config.root, structure, config.tree_depth)
        + "\n",
    )
    graph, external = build_import_graph(analyses)
    external_imports = {item for values in external.values() for item in values}
    bundle.text("requirements.txt", requirements_document(records, external_imports, generated_at))
    bundle.json("statistics.json", statistics_json(records, analyses, project, generated_at))
    bundle.json("api_manifest.json", api_manifest(analyses))
    _write_architecture(bundle, analyses, generated_at)

    groups: dict[str, list[FileRecord]] = {
        "root": [],
        "scripts": [],
        "docs": [],
        "compatibility": [],
    }
    for record in records:
        category = _category_for(record)
        groups.setdefault(category, []).append(record)
    for category in ("root", "scripts", "docs"):
        bundle.text(
            f"{category}.txt", module_document(category, groups[category], analyses, generated_at)
        )
    canonical_groups = set(groups) - {"root", "scripts", "docs", "compatibility"}
    for category in sorted({"misc"} | canonical_groups):
        bundle.text(
            Path("phasenox") / f"{category}.txt",
            module_document(
                f"phasenox.{category}", groups.get(category, []), analyses, generated_at
            ),
        )
    bundle.text(
        Path("brain") / "compatibility.txt",
        module_document(
            "brain compatibility namespace",
            groups["compatibility"],
            analyses,
            generated_at,
        ),
    )

    bundle.text(
        Path("reports") / "unused_files.txt", unused_files_document(analyses, graph, generated_at)
    )
    bundle.text(
        Path("reports") / "duplicate_names.txt",
        duplicate_names_document(duplicate_symbols(analyses), generated_at),
    )
    bundle.text(
        Path("reports") / "circular_imports.txt", cycles_document(find_cycles(graph), generated_at)
    )


def _write_architecture(bundle: ExportBundle, analyses: dict, generated_at: str) -> None:
    graph, _ = build_import_graph(analyses)
    bundle.json("architecture.json", architecture_json(analyses))
    bundle.text(Path("reports") / "import_graph.txt", import_graph_document(graph, generated_at))


def _write_module(
    bundle: ExportBundle,
    selector: str,
    records: list[FileRecord],
    analyses: dict,
    generated_at: str,
) -> None:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", selector).strip("_") or "module"
    legacy_only = all(
        record.relative_path.parts and record.relative_path.parts[0].casefold() == "brain"
        for record in records
    )
    package = "brain" if legacy_only else "phasenox"
    title = "brain compatibility namespace" if legacy_only else f"phasenox.{selector}"
    bundle.text(
        Path(package) / f"{safe_name}.txt",
        module_document(title, records, analyses, generated_at),
    )


def _finish(bundle: ExportBundle, output_dir: Path) -> None:
    manifest = bundle.finalize()
    print(f"Generated {len(bundle.artifacts)} files in: {output_dir}")
    print(f"Manifest: {manifest}")
    for artifact in bundle.artifacts[:8]:
        print(f"  - {artifact.path} ({artifact.bytes:,} bytes)")
    if len(bundle.artifacts) > 8:
        print(f"  - ... and {len(bundle.artifacts) - 8} more files")


def _category_for(record: FileRecord) -> str:
    parts = record.relative_path.parts
    if not parts:
        return "root"
    if parts[0].casefold() in {"scripts", "script"}:
        return "scripts"
    if parts[0].casefold() in {"docs", "doc"}:
        return "docs"
    package = parts[0].casefold()
    if package == "brain":
        return "compatibility"
    if package != "phasenox":
        return "root"
    if len(parts) > 2:
        return parts[1].casefold()
    if len(parts) == 2:
        module = Path(parts[1]).stem.casefold()
        return "misc" if module == "__init__" else module
    return "misc"
