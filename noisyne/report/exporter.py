from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from .models import SoundBrainReport


class ReportExporter:
    def to_dict(
        self,
        report: SoundBrainReport,
    ) -> dict:
        analysis = report.analysis
        if analysis is not None:
            analysis = self._sanitize_floats(analysis)

        return {
            "metadata": {
                "audio_type": report.audio_type,
                "source_type": report.source_type,
                "instrument": report.instrument,
                "is_full_mix": report.is_full_mix,
                "confidence": round(report.confidence, 2),
                "confidence_scores": report.confidence_scores,
                "status": report.status,
                "warnings": report.warnings,
            },
            "analysis": analysis,
            "intelligence": {
                "semantic_labels": [
                    {
                        "label": item.split(":")[0].strip(),
                        "confidence": round(
                            float(item.split(":")[1].strip()),
                            2,
                        ),
                    }
                    for item in report.semantic_labels
                ],
            },
            "engineering": {
                "score": report.score,
                "strengths": report.strengths,
                "issues": [
                    {
                        "title": issue.title,
                        "severity": issue.severity,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                        "confidence": issue.confidence,
                    }
                    for issue in report.issues
                ],
            },
            "mix_intelligence": {
                "root_causes": [
                    {
                        "symptom": cause.symptom,
                        "likely_causes": cause.likely_causes,
                        "priority": cause.priority,
                        "confidence": cause.confidence,
                    }
                    for cause in report.root_causes
                ],
                "prioritized_issues": [
                    {
                        "title": issue.title,
                        "severity": issue.severity,
                        "priority_score": issue.priority_score,
                        "user_action_order": issue.user_action_order,
                        "category": issue.category,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                        "confidence": issue.confidence,
                    }
                    for issue in report.prioritized_issues
                ],
                "processing_chain": [
                    {
                        "order": step.order,
                        "target": step.target,
                        "plugin_type": step.plugin_type,
                        "suggestion": step.suggestion,
                        "estimated_impact": step.estimated_impact,
                        "confidence": step.confidence,
                    }
                    for step in report.processing_chain
                ],
                "explanations": report.explanations,
            },
            "plugin_intelligence": self._serialize_plugin_intelligence(report.plugin_intelligence),
            "recommendations": report.recommendations,
            "summary": report.ai_summary,
        }

    def _sanitize_floats(self, data):
        """Replace non-finite floats with None for JSON-safe serialization."""
        import math

        if isinstance(data, float):
            if not math.isfinite(data):
                return None
            return data
        if isinstance(data, dict):
            return {key: self._sanitize_floats(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._sanitize_floats(item) for item in data]
        return data

    def _serialize_plugin_intelligence(
        self,
        plugin_result,
    ) -> dict | None:
        if plugin_result is None:
            return None

        return {
            "goals": [
                {
                    "id": goal.id,
                    "description": goal.description,
                    "target": goal.target,
                    "root_cause": goal.root_cause,
                    "action": goal.action,
                    "confidence": goal.confidence,
                }
                for goal in plugin_result.goals
            ],
            "steps": [
                {
                    "order": step.order,
                    "plugin_category": step.plugin_category,
                    "plugin_type": step.plugin_type,
                    "suggestion": step.suggestion,
                    "estimated_impact": step.estimated_impact,
                    "confidence": step.confidence,
                    "goal": {
                        "id": step.goal.id,
                        "description": step.goal.description,
                        "target": step.goal.target,
                        "action": step.goal.action,
                    },
                    "parameter_recommendations": [
                        {
                            "name": param.name,
                            "value": param.value,
                            "unit": param.unit,
                            "range_min": param.range_min,
                            "range_max": param.range_max,
                            "confidence": param.confidence,
                            "reason": param.reason,
                        }
                        for param in step.parameter_recommendations
                    ],
                    "plugin_options": [
                        {
                            "brand": option.brand,
                            "name": option.name,
                            "formats": option.formats,
                            "category": option.category,
                            "identifier": option.identifier,
                        }
                        for option in step.plugin_options
                    ],
                }
                for step in plugin_result.steps
            ],
            "explanations": plugin_result.explanations,
            "confidence_scores": plugin_result.confidence_scores,
        }

    def save_json(
        self,
        report: SoundBrainReport,
        path: str,
    ) -> None:
        data = self.to_dict(report)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to a temporary file in the same directory and rename
        # so consumers never see a partially-written report.
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                json.dump(data, temp_file, indent=4, ensure_ascii=False, allow_nan=False)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
        try:
            temp_path.replace(target)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
