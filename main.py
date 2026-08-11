from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path


def _reports_dir() -> Path:
    """Return the configured reports directory.

    Import is deferred to avoid heavy module-level imports until a
    command is actually executed.
    """
    from brain.infrastructure.config import settings

    return settings.runtime.report_dir


def _default_report_path(audio_path: str | Path, suffix: str = "") -> Path:
    audio_name = Path(audio_path).stem
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_dir = _reports_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{suffix}" if suffix else ""
    return output_dir / f"{timestamp}_{audio_name}{suffix}.json"


def _default_reference_output_directory(audio_path: str | Path) -> Path:
    """Return a directory for the JSON and Markdown reference reports."""
    audio_name = Path(audio_path).stem
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_dir = _reports_dir()
    return output_dir / f"{timestamp}_{audio_name}_reference"


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Run the V1 audio review flow through SoundBrainService."""
    from brain.application.soundbrain_service import (
        AnalysisRequest,
        SoundBrainService,
    )

    if args.output is None:
        args.output = _default_report_path(args.audio_path)

    reference_path = args.reference
    if reference_path is not None and len(reference_path) == 1:
        reference_path = reference_path[0]

    request = AnalysisRequest(
        audio_path=args.audio_path,
        reference_path=reference_path,
        intent=args.intent,
        delivery_target=args.delivery_target,
        reference_genre=args.reference_genre,
        reference_mood=args.reference_mood,
        reference_target=args.reference_target,
        reference_focus=args.reference_focus or [],
        include_reasoning=args.reasoning,
        include_rag=args.rag,
        include_semantic_analysis=args.semantic,
        include_mix_intelligence=args.mix_intelligence,
        include_plugin_intelligence=args.plugin_intelligence,
        output_path=args.output,
    )

    service = SoundBrainService()
    try:
        service.analyze(request)
    except Exception as exc:  # noqa: BLE001 — CLI top-level catch-all for user-facing error message
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1

    print(f"Report saved to: {args.output}")
    return 0


def _cmd_reference(args: argparse.Namespace) -> int:
    """Compare one or more reference audio files against the current mix."""
    from brain.application.soundbrain_service import (
        AnalysisRequest,
        SoundBrainService,
    )

    if args.output is None:
        args.output = _default_reference_output_directory(args.current)

    request = AnalysisRequest(
        audio_path=args.current,
        reference_path=args.reference,
        reference_genre=args.genre,
        reference_mood=args.mood,
        reference_target=args.target,
        reference_focus=args.focus or [],
        reference_output_directory=args.output,
    )

    service = SoundBrainService()
    try:
        response = service.analyze(request)
    except Exception as exc:  # noqa: BLE001 — CLI top-level catch-all for user-facing error message
        print(f"Reference comparison failed: {exc}", file=sys.stderr)
        return 1

    if response.comparison is None:
        print(
            "Reference comparison failed: no comparison produced.",
            file=sys.stderr,
        )
        return 1

    print(f"Reference reports saved to: {args.output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="soundbrain",
        description="SoundBrain — AI-powered Audio Intelligence Platform",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Available commands",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze an audio file and produce a deterministic engineering report.",
    )
    analyze_parser.add_argument(
        "audio_path",
        help="Path to the audio file to analyze.",
    )
    analyze_parser.add_argument(
        "--reference",
        dest="reference",
        action="append",
        help="Optional reference audio path for comparison. Can be repeated.",
    )
    analyze_parser.add_argument(
        "--output",
        "-o",
        dest="output",
        help="Output report path (default: reports/<timestamp>_<filename>.json).",
    )
    analyze_parser.add_argument(
        "--semantic",
        action="store_true",
        help="Include semantic analysis using CLAP embeddings (requires the CLAP model).",
    )
    analyze_parser.add_argument(
        "--reasoning",
        action="store_true",
        help="Include LLM reasoning over the analysis (requires an available LLM endpoint).",
    )
    analyze_parser.add_argument(
        "--rag",
        action="store_true",
        help="Include RAG retrieval for knowledge-backed reasoning (requires Chroma data).",
    )
    analyze_parser.add_argument(
        "--mix-intelligence",
        action="store_true",
        help="Include deterministic mix intelligence (root causes, priority chain, explanations).",
    )
    analyze_parser.add_argument(
        "--plugin-intelligence",
        action="store_true",
        help="Include plugin-aware recommendations and parameter suggestions (requires mix intelligence).",
    )
    analyze_parser.add_argument(
        "--intent",
        default="",
        help="Optional human-provided intent context included in reasoning and report.",
    )
    analyze_parser.add_argument(
        "--delivery-target",
        default="",
        help="Optional delivery target (e.g. streaming, club, vinyl) included in reasoning and report.",
    )
    analyze_parser.add_argument(
        "--reference-genre",
        default=None,
        help="Reference genre context for style-aware comparison.",
    )
    analyze_parser.add_argument(
        "--reference-mood",
        default=None,
        help="Reference mood context for style-aware comparison.",
    )
    analyze_parser.add_argument(
        "--reference-target",
        default=None,
        help="Reference delivery target (streaming, club, vinyl, etc.).",
    )
    analyze_parser.add_argument(
        "--reference-focus",
        default=None,
        nargs="+",
        help="Focus areas for reference comparison (e.g. loudness dynamics stereo).",
    )

    reference_parser = subparsers.add_parser(
        "reference",
        help="Compare one or more reference audio files against the current mix.",
    )
    reference_parser.add_argument(
        "current",
        help="Path to the current/mix audio file.",
    )
    reference_parser.add_argument(
        "reference",
        nargs="+",
        help="One or more reference audio file paths.",
    )
    reference_parser.add_argument(
        "--output",
        "-o",
        dest="output",
        help="Output directory for reference_report.json and reference_report.md.",
    )
    reference_parser.add_argument(
        "--genre",
        default=None,
        help="Reference genre context for style-aware comparison.",
    )
    reference_parser.add_argument(
        "--mood",
        default=None,
        help="Reference mood context for style-aware comparison.",
    )
    reference_parser.add_argument(
        "--target",
        default=None,
        help="Reference delivery target (streaming, club, vinyl, etc.).",
    )
    reference_parser.add_argument(
        "--focus",
        default=None,
        nargs="+",
        help="Focus areas for reference comparison (e.g. loudness dynamics stereo).",
    )

    args = parser.parse_args(argv)

    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "reference":
        return _cmd_reference(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
