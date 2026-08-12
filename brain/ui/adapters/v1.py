"""V1 backend adapter for stable, Qt-free desktop contracts."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..branding import default_product_metadata
from ..contracts import (
    AnalysisCommand,
    AnalysisIssue,
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    MetricValue,
    PathStatus,
    ProductMetadata,
    ProviderStatus,
    ReferenceBandDifference,
    ReferenceComparisonCommand,
    ReferenceFinding,
    ReferenceMetric,
    ReferenceSegmentDeviation,
    ReferenceSimilarity,
    ReferenceViewResult,
    ReportDescriptor,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
    SettingValue,
)


class V1ApplicationAdapter:
    """Translate frozen V1 facades and domain results into desktop contracts."""

    def __init__(
        self,
        *,
        metadata: ProductMetadata | None = None,
        service_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._metadata = metadata or default_product_metadata()
        self._service_factory = service_factory

    def product_metadata(self) -> ProductMetadata:
        return self._metadata

    def capability_snapshots(self) -> tuple[CapabilitySnapshot, ...]:
        # V1 capability records are backend-specific and intentionally imported
        # only inside this adapter.
        from brain.runtime.capabilities import registry

        snapshots: list[CapabilitySnapshot] = []
        for capability in registry:
            lifecycle = CapabilityLifecycle(capability.status.value)
            if lifecycle is CapabilityLifecycle.PLANNED:
                availability = Availability.UNAVAILABLE
                reason_code = "lifecycle_planned"
                reason = capability.reason_unavailable or "This capability is planned."
            else:
                availability = Availability.UNKNOWN
                reason_code = "availability_not_probed"
                reason = "Availability has not been checked on this machine."

            snapshots.append(
                CapabilitySnapshot(
                    id=capability.name,
                    display_name=capability.description,
                    lifecycle=lifecycle,
                    availability=availability,
                    reason_code=reason_code,
                    reason=reason,
                    dependencies=tuple(capability.dependencies),
                )
            )
        return tuple(snapshots)

    def runtime_status(self) -> RuntimeStatus:
        # This is a lightweight status snapshot. It does not import Torch or
        # initialize providers/models; those probes remain indeterminate.
        from brain.infrastructure.config import settings

        checked_at = datetime.now(UTC)
        paths = tuple(
            self._path_status(kind, path)
            for kind, path in (
                ("model_root", settings.runtime.model_root),
                ("cache", settings.runtime.cache_dir),
                ("logs", settings.runtime.log_dir),
                ("reports", settings.runtime.report_dir),
            )
        )
        return RuntimeStatus(
            state=RuntimeState.UNKNOWN,
            requested_device=settings.runtime.device,
            effective_device=None,
            device_reason="Device availability has not been probed.",
            loaded_models=(),
            provider=ProviderStatus(
                name=settings.llm.provider,
                availability=Availability.UNKNOWN,
                reason="Provider availability has not been probed.",
            ),
            paths=paths,
            configuration_source="packaged_default",
            capabilities=self.capability_snapshots(),
            checked_at=checked_at,
        )

    def settings_snapshot(self) -> SettingsSnapshot:
        from brain.infrastructure.config import settings

        values = (
            SettingValue("runtime.device", settings.runtime.device),
            SettingValue("runtime.dtype", settings.runtime.dtype),
            SettingValue("runtime.model_root", str(settings.runtime.model_root)),
            SettingValue("runtime.report_dir", str(settings.runtime.report_dir)),
            SettingValue("audio.sample_rate", settings.audio.sample_rate),
            SettingValue("audio.max_duration_seconds", settings.audio.max_duration_seconds),
            SettingValue("llm.provider", settings.llm.provider),
            SettingValue("llm.model", settings.llm.model),
            SettingValue("llm.base_url", settings.llm.base_url),
        )
        return SettingsSnapshot(
            revision="packaged-v1",
            source="packaged_default",
            values=values,
            credential_configured=bool(settings.llm.api_key),
        )

    def analyze(self, command: AnalysisCommand) -> AnalysisViewResult:
        service, request_type = self._analysis_boundary()
        reference_path: list[Path] | None = list(command.reference_paths) or None
        response = service.analyze(
            request_type(
                audio_path=command.source_path,
                reference_path=reference_path,
                intent=command.intent,
                delivery_target=command.delivery_target,
                include_reasoning=command.include_reasoning,
                include_rag=command.include_rag,
                include_semantic_analysis=command.include_semantic_analysis,
                include_mix_intelligence=command.include_mix_intelligence,
                include_plugin_intelligence=command.include_plugin_intelligence,
                output_path=command.output_path,
            )
        )
        report = response.report
        issues = tuple(
            AnalysisIssue(
                title=str(issue.title),
                severity=str(issue.severity),
                description=str(issue.description),
                recommendation=str(issue.recommendation),
            )
            for issue in report.issues
        )
        reports: tuple[ReportDescriptor, ...] = ()
        if command.output_path is not None and command.output_path.exists():
            reports = (
                ReportDescriptor(
                    kind="analysis",
                    format="json",
                    path=command.output_path,
                    display_label=command.output_path.name,
                ),
            )
        comparison = getattr(response, "comparison", None)
        return AnalysisViewResult(
            source_path=command.source_path,
            status=str(response.status),
            audio_type=str(report.audio_type),
            score=float(report.score),
            summary=str(report.ai_summary),
            issues=issues,
            metrics=self._scalar_metrics(response.analysis),
            warnings=tuple(str(item) for item in response.warnings),
            reference_similarity=(float(comparison.similarity) if comparison is not None else None),
            reports=reports,
        )

    def compare_references(self, command: ReferenceComparisonCommand) -> ReferenceViewResult:
        service, request_type = self._analysis_boundary()
        reference_path: Path | list[Path]
        if len(command.reference_paths) == 1:
            reference_path = command.reference_paths[0]
        else:
            reference_path = list(command.reference_paths)
        response = service.analyze(
            request_type(
                audio_path=command.current_path,
                reference_path=reference_path,
                reference_output_directory=command.output_directory,
                reference_genre=command.genre or None,
                reference_mood=command.mood or None,
                reference_target=command.target or None,
                reference_focus=list(command.focus_areas),
            )
        )
        comparison = getattr(response, "comparison", None)
        reports = self._reference_reports(command.output_directory)
        if comparison is None:
            return ReferenceViewResult(
                current_path=command.current_path,
                reference_paths=command.reference_paths,
                status=str(response.status),
                similarity=None,
                confidence=None,
                warnings=tuple(str(item) for item in response.warnings),
                reports=reports,
            )

        scores = tuple(
            MetricValue(name, float(getattr(comparison, field_name)))
            for name, field_name in (
                ("frequency_score", "frequency_score"),
                ("dynamic_score", "dynamic_score"),
                ("stereo_score", "stereo_score"),
                ("loudness_score", "loudness_score"),
                ("transient_score", "transient_score"),
                ("phase_score", "phase_score"),
                ("tonal_score", "tonal_score"),
                ("semantic_score", "semantic_score"),
            )
        )
        metrics = tuple(
            ReferenceMetric(
                name=str(item.name),
                current=float(item.current),
                reference=float(item.reference),
                difference=float(item.difference),
                unit=str(item.unit),
                tolerance=float(item.tolerance),
                passed=bool(item.passed),
                severity=self._enum_value(item.severity),
                similarity=float(item.similarity),
            )
            for item in comparison.metrics
        )
        bands = tuple(
            ReferenceBandDifference(
                band=str(item.band),
                start_hz=float(item.start_hz),
                end_hz=float(item.end_hz),
                reference_energy=float(item.reference_energy),
                current_energy=float(item.current_energy),
                difference_db=float(item.difference_db),
                severity=self._enum_value(item.severity),
            )
            for item in comparison.band_differences
        )
        findings = tuple(
            ReferenceFinding(
                title=str(item.title),
                description=str(item.description),
                category=self._enum_value(item.category),
                severity=self._enum_value(item.severity),
                confidence=float(item.confidence),
                recommendation=str(item.recommendation),
                decision_type=self._enum_value(item.decision_type),
            )
            for item in comparison.engineer_decisions
        )
        per_reference = tuple(
            ReferenceSimilarity(Path(path), float(similarity))
            for path, similarity in comparison.reference_similarities.items()
        )
        segments = tuple(
            ReferenceSegmentDeviation(
                start_time=float(item.start_time),
                end_time=float(item.end_time),
                metric=str(item.metric),
                reference_value=float(item.reference_value),
                current_value=float(item.current_value),
                severity=str(item.severity),
            )
            for item in comparison.segment_deviations
        )
        variances = tuple(
            MetricValue(str(name), float(value))
            for name, value in comparison.metric_variance.items()
        )
        return ReferenceViewResult(
            current_path=command.current_path,
            reference_paths=command.reference_paths,
            status=str(response.status),
            similarity=float(comparison.similarity),
            confidence=float(comparison.confidence),
            scores=scores,
            metric_variances=variances,
            metrics=metrics,
            band_differences=bands,
            findings=findings,
            reference_similarities=per_reference,
            segment_deviations=segments,
            warnings=tuple(str(item) for item in response.warnings),
            reports=reports,
        )

    def _analysis_boundary(self) -> tuple[Any, type[Any]]:
        from brain.application.soundbrain_service import AnalysisRequest, SoundBrainService

        factory = self._service_factory or SoundBrainService
        return factory(), AnalysisRequest

    @staticmethod
    def _reference_reports(output_directory: Path | None) -> tuple[ReportDescriptor, ...]:
        if output_directory is None:
            return ()
        descriptors = []
        for format_name, filename, label in (
            ("json", "reference_report.json", "Reference report JSON"),
            ("markdown", "reference_report.md", "Reference report Markdown"),
        ):
            path = output_directory / filename
            if path.exists():
                descriptors.append(
                    ReportDescriptor(
                        kind="reference_comparison",
                        format=format_name,
                        path=path,
                        display_label=label,
                    )
                )
        return tuple(descriptors)

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _scalar_metrics(value: Any) -> tuple[MetricValue, ...]:
        if not is_dataclass(value) or isinstance(value, type):
            return ()
        scalar_types = (str, int, float, bool, type(None))
        return tuple(
            MetricValue(item.name, field_value)
            for item in fields(value)
            if isinstance((field_value := getattr(value, item.name)), scalar_types)
        )

    @staticmethod
    def _path_status(kind: str, raw_path: str | Path) -> PathStatus:
        path = Path(raw_path)
        probe = path if path.exists() else path.parent
        return PathStatus(
            kind=kind,
            path=path,
            exists=path.exists(),
            readable=probe.exists() and os.access(probe, os.R_OK),
            writable=probe.exists() and os.access(probe, os.W_OK),
        )
