"""Generate the V1 release validation report."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from noisyne.providers import ProviderFactory, ProviderService
from noisyne.providers.mock import MockProvider
from noisyne.providers.models import GenerateRequest

REPORTS_DIR = PROJECT_ROOT / "reports"
VALIDATION_PATH = REPORTS_DIR / "v1_release_validation.json"


def run_command(cmd: list[str]) -> dict:
    """Run a shell command and return a structured result."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    return {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout[-2000:] if result.stdout else "",
        "stderr": result.stderr[-2000:] if result.stderr else "",
    }


def parse_pytest_summary(output: str) -> dict:
    """Parse pytest summary line for pass/fail/skip counts."""
    summary = {"passed": 0, "failed": 0, "skipped": 0, "error": 0, "duration": 0.0}
    match = re.search(
        r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?:, (\d+) error)? in ([\d.]+)s",
        output,
    )
    if match:
        summary["passed"] = int(match.group(1) or 0)
        summary["failed"] = int(match.group(2) or 0)
        summary["skipped"] = int(match.group(3) or 0)
        summary["error"] = int(match.group(4) or 0)
        summary["duration"] = float(match.group(5))
    return summary


VALIDATED_FILES = [
    # Sprint 12 modified files.
    "noisyne/infrastructure/config/models.py",
    "noisyne/infrastructure/config/loader.py",
    "noisyne/llm/qwen.py",
    "noisyne/embedding.py",
    "noisyne/rag/reranker.py",
    "noisyne/text/embeddings/providers/sentence_transformer.py",
    "noisyne/audio/plugin/parameter_generator.py",
    "noisyne/report/exporter.py",
    "noisyne/report/models.py",
    "noisyne/application/soundbrain_service.py",
    "noisyne/reasoning/parser.py",
    "noisyne/providers/factory.py",
    "noisyne/rag/pdf_ocr_loader.py",
    "scripts/generate_v1_release_validation.py",
]


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    python = str(PROJECT_ROOT / "venv" / "Scripts" / "python")

    validation = {
        "metadata": {
            "version": "1.0.0-rc1",
            "timestamp": datetime.now(UTC).isoformat(),
            "purpose": "SoundBrain V1 release candidate validation",
        },
        "formatting": run_command([python, "-m", "black", "--check"] + VALIDATED_FILES),
        "lint": run_command([python, "-m", "ruff", "check"] + VALIDATED_FILES),
        "compileall": run_command([python, "-m", "compileall", "brain", "tests"]),
        "tests": {},
        "cli": {},
        "workflow_export": {},
        "evaluation": {},
        "provider_layer": {},
    }

    test_files = [
        "tests/test_providers_factory.py",
        "tests/test_providers_mock.py",
        "tests/test_providers_reasoning.py",
        "tests/test_soundbrain_service_reasoning.py",
        "tests/test_runtime.py",
        "tests/test_engine_registry.py",
        "tests/test_rag_collection.py",
        "tests/test_soundbrain_service.py",
        "tests/test_soundbrain_service_integration.py",
        "tests/test_reference_pipeline.py",
        "tests/test_reference_intelligence.py",
        "tests/test_reference_reasoner.py",
        "tests/test_audio_pipeline.py",
        "tests/test_root_cause.py",
        "tests/test_priority_engine.py",
        "tests/test_processing_chain.py",
        "tests/test_mix_explanation.py",
        "tests/test_plugin_chain_builder.py",
        "tests/test_plugin_intelligence_service.py",
        "tests/test_plugin_parameter_generator.py",
        "tests/test_plugin_registry.py",
        "tests/test_plugin_selector.py",
        "tests/test_plugin_validator.py",
        "tests/test_knowledge_loader.py",
        "tests/test_knowledge_registry.py",
        "tests/test_knowledge_resolver.py",
        "tests/test_knowledge_service.py",
        "tests/test_knowledge_validator.py",
        "tests/test_memory_loader.py",
        "tests/test_memory_registry.py",
        "tests/test_memory_resolver.py",
        "tests/test_memory_service.py",
        "tests/test_evaluation_metrics.py",
        "tests/test_evaluation_scoring.py",
        "tests/test_evaluation_service.py",
        "tests/test_integration_factory.py",
        "tests/test_integration_adapters.py",
    ]

    test_result = run_command(
        [python, "-m", "pytest", "-q", "--tb=short", "-p", "no:faulthandler"] + test_files
    )
    summary = parse_pytest_summary(test_result["stdout"] + test_result["stderr"])
    validation["tests"] = {
        "command": test_result["command"],
        "passed": test_result["passed"],
        "exit_code": test_result["returncode"],
        "summary": summary,
        "stdout": test_result["stdout"][-2000:],
        "stderr": test_result["stderr"][-2000:],
    }

    # CLI validation.
    cli_report_path = REPORTS_DIR / "v1_release_cli.json"
    validation["cli"] = run_command(
        [
            python,
            "main.py",
            "analyze",
            "tests/audio.wav",
            "--reasoning",
            "--output",
            str(cli_report_path),
        ]
    )
    validation["cli"]["report_exists"] = cli_report_path.exists()

    # Workflow export validation.
    workflow_output = PROJECT_ROOT / "outputs" / "v1_release_workflow"
    try:
        from noisyne.audio.mix.models import MixIntelligenceResult, ProcessingStep
        from noisyne.audio.plugin.models import (
            PluginIntelligenceResult,
            PluginIntelligenceStep,
            ProcessingGoal,
        )
        from noisyne.integration import AdapterFactory, ExportRequest, WorkflowSession
        from noisyne.report.models import ReportIssue, SoundBrainReport

        workflow_output.mkdir(parents=True, exist_ok=True)
        report = SoundBrainReport(
            audio_type="full_mix",
            source_type="file",
            instrument=None,
            is_full_mix=True,
            confidence=0.9,
            score=80.0,
            issues=[
                ReportIssue(
                    title="harsh highs",
                    severity="medium",
                    description="2-5 kHz elevated",
                    recommendation="gentle EQ cut",
                ),
            ],
            recommendations=["reduce 3 kHz"],
        )
        goal = ProcessingGoal(
            id="g1",
            description="smooth highs",
            target="frequency_balance",
            root_cause="harsh highs",
            action="EQ cut",
            confidence=0.85,
        )
        mix = MixIntelligenceResult(
            processing_chain=[
                ProcessingStep(
                    order=1,
                    target="frequency_balance",
                    plugin_type="EQ",
                    suggestion="reduce 2-5 kHz",
                    estimated_impact="high",
                    confidence=0.85,
                ),
            ],
        )
        plugin = PluginIntelligenceResult(
            goals=[goal],
            steps=[
                PluginIntelligenceStep(
                    order=1,
                    goal=goal,
                    plugin_category="EQ",
                    plugin_type="parametric_eq",
                    suggestion="cut 3 kHz",
                    estimated_impact="high",
                    confidence=0.85,
                ),
            ],
        )
        request = ExportRequest(
            session=WorkflowSession(daw_name="ableton"),
            output_dir=workflow_output,
            report=report,
            mix_intelligence=mix,
            plugin_intelligence=plugin,
        )
        for adapter_name in AdapterFactory.list():
            adapter = AdapterFactory.get(adapter_name)
            adapter.export_analysis(request)
            adapter.export_processing_chain(request)
            adapter.export_plugin_recommendations(request)
            adapter.export_report(request)
        validation["workflow_export"] = {
            "passed": True,
            "adapters": AdapterFactory.list(),
            "output_dir": str(workflow_output.relative_to(PROJECT_ROOT)),
            "error": None,
        }
    except (
        ImportError,
        AttributeError,
        ValueError,
        TypeError,
        OSError,
        RuntimeError,
    ) as exc:
        validation["workflow_export"] = {
            "passed": False,
            "adapters": [],
            "output_dir": None,
            "error": str(exc),
        }

    # Evaluation validation.
    eval_report_path = REPORTS_DIR / "v1_release_evaluation.json"
    try:
        from noisyne.evaluation.service import EvaluationService

        eval_service = EvaluationService()
        eval_result = eval_service.evaluate_components(report)
        eval_report_path.write_text(
            json.dumps(eval_result, indent=4, default=str),
            encoding="utf-8",
        )
        validation["evaluation"] = {
            "passed": True,
            "report_path": str(eval_report_path.relative_to(PROJECT_ROOT)),
            "error": None,
        }
    except (
        ImportError,
        AttributeError,
        ValueError,
        TypeError,
        OSError,
        RuntimeError,
    ) as exc:
        validation["evaluation"] = {
            "passed": False,
            "report_path": None,
            "error": str(exc),
        }

    # Provider layer validation.
    try:
        service = ProviderService(provider=MockProvider())
        response = service.generate(GenerateRequest(user_prompt="V1 release validation"))
        validation["provider_layer"] = {
            "passed": True,
            "default_provider": ProviderFactory.default().name,
            "mock_response_provider": response.provider,
            "error": None,
        }
    except (
        ImportError,
        AttributeError,
        ValueError,
        TypeError,
        OSError,
        RuntimeError,
    ) as exc:
        validation["provider_layer"] = {
            "passed": False,
            "default_provider": None,
            "mock_response_provider": None,
            "error": str(exc),
        }

    # Overall status.
    checks = [
        validation["formatting"]["passed"],
        validation["lint"]["passed"],
        validation["compileall"]["passed"],
        validation["tests"]["passed"],
        validation["cli"]["passed"],
        validation["cli"]["report_exists"],
        validation["workflow_export"]["passed"],
        validation["evaluation"]["passed"],
        validation["provider_layer"]["passed"],
    ]
    validation["overall"] = {
        "passed": all(checks),
        "checks_passed": sum(checks),
        "checks_total": len(checks),
    }

    VALIDATION_PATH.write_text(
        json.dumps(validation, indent=4, default=str),
        encoding="utf-8",
    )
    print(f"Validation report written to: {VALIDATION_PATH}")
    return 0 if validation["overall"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
