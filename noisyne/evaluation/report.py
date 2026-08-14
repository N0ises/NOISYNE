from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BenchmarkResult, EvaluationResult


class EvaluationReportExporter:
    """Export evaluation results to JSON."""

    def to_dict(self, result: EvaluationResult | BenchmarkResult) -> dict[str, Any]:
        """Convert a result into a plain JSON-serializable dictionary."""
        from dataclasses import asdict

        return asdict(result)

    def save_json(
        self,
        result: EvaluationResult | BenchmarkResult,
        path: str | Path,
    ) -> Path:
        """Save a result to a JSON file and return the path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(result), indent=2, default=str),
            encoding="utf-8",
        )
        return path
