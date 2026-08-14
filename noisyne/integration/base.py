from __future__ import annotations

import enum
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, ClassVar

from .models import DAWCapability, ExportRequest, ExportResult


def _to_serializable(value: Any) -> Any:
    """Convert dataclasses and enums to plain JSON-serializable structures."""
    if is_dataclass(value) and not isinstance(value, type):
        return _to_serializable(asdict(value))
    if isinstance(value, dict):
        return {k: _to_serializable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_to_serializable(v) for v in value]
    if isinstance(value, enum.Enum):
        return value.value
    return value


class WorkflowAdapter(ABC):
    """
    Abstract contract for exporting SoundBrain results to an external workflow.

    Implementations in this sprint are deterministic placeholders. They do not
    communicate with any DAW, API, or external process.
    """

    name: ClassVar[str]

    @abstractmethod
    def capabilities(self) -> list[DAWCapability]: ...

    @abstractmethod
    def export_analysis(self, request: ExportRequest) -> ExportResult: ...

    @abstractmethod
    def export_processing_chain(self, request: ExportRequest) -> ExportResult: ...

    @abstractmethod
    def export_plugin_recommendations(self, request: ExportRequest) -> ExportResult: ...

    @abstractmethod
    def export_report(self, request: ExportRequest) -> ExportResult: ...


class BaseWorkflowAdapter(WorkflowAdapter, ABC):
    """
    Deterministic placeholder adapter for DAW workflow contracts.

    Subclasses only need to set ``name`` and override ``capabilities()``.
    All export methods write safe placeholder files to
    ``request.output_dir / <adapter_name>`` and never communicate with a DAW.
    """

    def _adapter_dir(self, request: ExportRequest) -> Path:
        target = request.output_dir / self.name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _write_json(self, path: Path, data: Any) -> Path:
        path.write_text(
            json.dumps(_to_serializable(data), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _write_text(self, path: Path, content: str) -> Path:
        path.write_text(content, encoding="utf-8")
        return path

    def _base_payload(self, request: ExportRequest) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "daw": request.session.daw_name,
            "project": request.session.project_name,
            "sample_rate": request.session.sample_rate,
            "bpm": request.session.bpm,
            "time_signature": request.session.time_signature,
            "metadata": request.session.metadata,
        }

    def export_analysis(self, request: ExportRequest) -> ExportResult:
        target = self._adapter_dir(request)
        payload = self._base_payload(request)
        payload["analysis"] = {
            "audio_type": request.report.audio_type if request.report else None,
            "score": request.report.score if request.report else None,
            "strengths": request.report.strengths if request.report else [],
            "issues": [
                {"title": issue.title, "severity": issue.severity}
                for issue in (request.report.issues if request.report else [])
            ],
        }
        files = [self._write_json(target / "analysis.json", payload)]
        return ExportResult(
            adapter_name=self.name,
            export_type="analysis",
            success=True,
            files=files,
            notes=["Placeholder analysis export. No DAW communication occurred."],
            capabilities=[cap.name for cap in self.capabilities()],
        )

    def export_processing_chain(self, request: ExportRequest) -> ExportResult:
        target = self._adapter_dir(request)
        payload = self._base_payload(request)
        chain = []
        if request.mix_intelligence:
            chain = [
                {
                    "order": step.order,
                    "target": step.target,
                    "plugin_type": step.plugin_type,
                    "suggestion": step.suggestion,
                    "estimated_impact": step.estimated_impact,
                }
                for step in request.mix_intelligence.processing_chain
            ]
        payload["processing_chain"] = chain
        files = [
            self._write_json(target / "processing_chain.json", payload),
            self._write_text(
                target / "processing_chain.txt",
                (
                    f"# {self.name} processing chain\n\n"
                    + "\n".join(
                        f"{step['order']}. {step['target']} ({step['plugin_type']})"
                        for step in chain
                    )
                    if chain
                    else "No processing chain available."
                ),
            ),
        ]
        return ExportResult(
            adapter_name=self.name,
            export_type="processing_chain",
            success=True,
            files=files,
            notes=["Placeholder processing chain export. No DAW communication occurred."],
            capabilities=[cap.name for cap in self.capabilities()],
        )

    def export_plugin_recommendations(self, request: ExportRequest) -> ExportResult:
        target = self._adapter_dir(request)
        payload = self._base_payload(request)
        recommendations = []
        if request.plugin_intelligence:
            recommendations = [
                {
                    "order": step.order,
                    "plugin_category": step.plugin_category,
                    "plugin_type": step.plugin_type,
                    "suggestion": step.suggestion,
                    "estimated_impact": step.estimated_impact,
                    "parameters": [
                        {
                            "name": param.name,
                            "value": param.value,
                            "unit": param.unit,
                        }
                        for param in step.parameter_recommendations
                    ],
                }
                for step in request.plugin_intelligence.steps
            ]
        payload["plugin_recommendations"] = recommendations
        files = [self._write_json(target / "plugin_recommendations.json", payload)]
        return ExportResult(
            adapter_name=self.name,
            export_type="plugin_recommendations",
            success=True,
            files=files,
            notes=["Placeholder plugin recommendation export. No DAW communication occurred."],
            capabilities=[cap.name for cap in self.capabilities()],
        )

    def export_report(self, request: ExportRequest) -> ExportResult:
        target = self._adapter_dir(request)
        payload = self._base_payload(request)
        payload["report"] = {
            "audio_type": request.report.audio_type if request.report else None,
            "score": request.report.score if request.report else None,
            "ai_summary": request.report.ai_summary if request.report else "",
            "recommendations": request.report.recommendations if request.report else [],
        }
        files = [
            self._write_json(target / "report.json", payload),
            self._write_text(
                target / "report.md",
                (
                    f"# {self.name} Report Export\n\n"
                    f"**Project:** {request.session.project_name or 'Untitled'}\n\n"
                    f"**Audio type:** {request.report.audio_type if request.report else 'N/A'}\n\n"
                    f"**Score:** {request.report.score if request.report else 'N/A'}\n\n"
                    "## Recommendations\n\n"
                    + "\n".join(
                        f"- {rec}"
                        for rec in (request.report.recommendations if request.report else [])
                    )
                    if request.report and request.report.recommendations
                    else "No recommendations available."
                ),
            ),
        ]
        return ExportResult(
            adapter_name=self.name,
            export_type="report",
            success=True,
            files=files,
            notes=["Placeholder report export. No DAW communication occurred."],
            capabilities=[cap.name for cap in self.capabilities()],
        )
