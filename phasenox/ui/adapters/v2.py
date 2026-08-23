"""Canonical backend adapter for stable, Qt-free Desktop contracts."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, ClassVar

from ..branding import default_product_metadata
from ..contracts import (
    AnalysisCommand,
    AnalysisIssue,
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    IntelligenceEvidence,
    IntelligenceItem,
    IntelligenceParameter,
    IntelligenceSnapshot,
    KnowledgeQuery,
    KnowledgeResultItem,
    KnowledgeSearchResult,
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
    ReportExportCommand,
    ReportExportResult,
    ReportPreview,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
    SettingValue,
)


class V2ApplicationAdapter:
    """Translate canonical PHASENOX facades and domain results into desktop contracts."""

    _MAX_REPORT_PREVIEW_BYTES = 2 * 1024 * 1024
    _REPORT_FORMATS: ClassVar[dict[str, frozenset[str]]] = {
        "analysis": frozenset({"json"}),
        "reference_comparison": frozenset({"json", "markdown"}),
    }
    _REPORT_EXTENSIONS: ClassVar[dict[str, str]] = {
        "json": ".json",
        "markdown": ".md",
    }

    def __init__(
        self,
        *,
        metadata: ProductMetadata | None = None,
        service_factory: Callable[[], Any] | None = None,
        v2_service_factory: Callable[[], Any] | None = None,
        rag_service_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._metadata = metadata or default_product_metadata()
        self._service_factory = service_factory
        self._v2_service_factory = v2_service_factory
        self._rag_service_factory = rag_service_factory

    def product_metadata(self) -> ProductMetadata:
        return self._metadata

    def capability_snapshots(self) -> tuple[CapabilitySnapshot, ...]:
        """Return lifecycle, dependency, and freeze evidence without claiming readiness."""
        from phasenox.runtime.capabilities import registry

        readiness_required = {"clap_embedding", "llm_reasoning", "rag_retrieval"}
        hidden_capabilities = {"audio_intelligence", "daw_integration", "memory_learning"}

        snapshots: list[CapabilitySnapshot] = []
        for capability in registry:
            lifecycle = CapabilityLifecycle(capability.status.value)
            dependency_state = self._dependency_package_state(capability.dependencies)
            if lifecycle is CapabilityLifecycle.PLANNED:
                availability = Availability.UNAVAILABLE
                reason_code = "lifecycle_planned"
                reason = capability.reason_unavailable or "This capability is planned."
                readiness_source = "lifecycle"
            elif capability.name in hidden_capabilities:
                availability = Availability.UNAVAILABLE
                reason_code = "not_exposed_in_desktop"
                reason = "This capability is not exposed in Sprint 17B Desktop."
                readiness_source = "desktop_feature_policy"
            elif capability.name in readiness_required:
                availability = Availability.UNAVAILABLE
                reason_code = "readiness_not_validated"
                reason = capability.reason_unavailable or (
                    "Package presence does not prove provider, model, or corpus readiness."
                )
                readiness_source = "readiness_required"
            elif dependency_state == "unavailable":
                availability = Availability.UNAVAILABLE
                reason_code = "dependency_unavailable"
                reason = capability.reason_unavailable or "A required dependency is unavailable."
                readiness_source = "dependency_probe"
            elif dependency_state == "unknown":
                availability = Availability.UNKNOWN
                reason_code = "dependency_unknown"
                reason = "Dependency availability could not be determined."
                readiness_source = "dependency_probe"
            elif capability.tested_in_freeze:
                availability = Availability.AVAILABLE
                reason_code = None
                reason = None
                readiness_source = "freeze_test_and_dependency_probe"
            else:
                availability = Availability.UNKNOWN
                reason_code = "readiness_not_attested"
                reason = "Dependencies are importable, but runtime readiness is not attested."
                readiness_source = "dependency_probe_only"

            snapshots.append(
                CapabilitySnapshot(
                    id=capability.name,
                    display_name=capability.description,
                    lifecycle=lifecycle,
                    availability=availability,
                    reason_code=reason_code,
                    reason=reason,
                    dependencies=tuple(capability.dependencies),
                    tested_in_freeze=capability.tested_in_freeze,
                    readiness_source=readiness_source,
                )
            )
        return tuple(snapshots)

    @staticmethod
    def _dependency_package_state(dependencies: tuple[str, ...]) -> str:
        """Probe package presence without importing heavy frameworks or providers."""
        if not dependencies:
            return "available"
        states: list[str] = []
        for dependency in dependencies:
            module_name = dependency.replace("-", "_")
            if not module_name.isidentifier():
                states.append("unknown")
                continue
            try:
                states.append(
                    "available" if importlib.util.find_spec(module_name) is not None else "unavailable"
                )
            except (ImportError, ModuleNotFoundError, ValueError):
                states.append("unknown")
        if "unavailable" in states:
            return "unavailable"
        if "unknown" in states:
            return "unknown"
        return "available"

    def runtime_status(self) -> RuntimeStatus:
        # This is a lightweight status snapshot. It does not import Torch or
        # initialize providers/models; those probes remain indeterminate.
        from phasenox.infrastructure.config import settings

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
        from phasenox.infrastructure.config import get_application_root, settings

        read_only = "Sprint 17B has no validated user-settings persistence contract."

        def value(
            key: str,
            raw_value: str | float | bool | Path,
            category: str,
            label: str,
        ) -> SettingValue:
            return SettingValue(
                key,
                str(raw_value) if isinstance(raw_value, Path) else raw_value,
                category=category,
                display_name=label,
                read_only_reason=read_only,
            )

        values = (
            value("llm.provider", settings.llm.provider, "provider", "Provider"),
            value("llm.model", settings.llm.model, "provider", "Configured model"),
            value("llm.base_url", settings.llm.base_url, "provider", "Base URL"),
            value("llm.temperature", settings.llm.temperature, "provider", "Temperature"),
            value("llm.top_p", settings.llm.top_p, "provider", "Top P"),
            value("llm.max_tokens", settings.llm.max_tokens, "provider", "Maximum tokens"),
            value("runtime.device", settings.runtime.device, "runtime", "Requested device"),
            value("runtime.dtype", settings.runtime.dtype, "runtime", "Requested data type"),
            value("runtime.lazy_load", settings.runtime.lazy_load, "runtime", "Lazy loading"),
            value("runtime.model_root", settings.runtime.model_root, "runtime", "Model root"),
            value(
                "application.root",
                get_application_root(),
                "runtime",
                "Application root",
            ),
            value("models.clap.name", settings.models.clap.name, "models", "CLAP model"),
            value("models.qwen.name", settings.models.qwen.name, "models", "Qwen model"),
            value(
                "models.bge_reranker.name",
                settings.models.bge_reranker.name,
                "models",
                "Reranker model",
            ),
            value(
                "models.text_embedding.name",
                settings.models.text_embedding.name,
                "models",
                "Text embedding model",
            ),
            value("audio.sample_rate", settings.audio.sample_rate, "audio", "Sample rate"),
            value(
                "audio.clap_target_sample_rate",
                settings.audio.clap_target_sample_rate,
                "audio",
                "CLAP target sample rate",
            ),
            value(
                "audio.max_duration_seconds",
                settings.audio.max_duration_seconds,
                "audio",
                "Maximum duration (seconds)",
            ),
            value("audio.n_fft", settings.audio.n_fft, "audio", "FFT size"),
            value("audio.hop_length", settings.audio.hop_length, "audio", "Hop length"),
            value("audio.n_mels", settings.audio.n_mels, "audio", "Mel bands"),
            value("audio.n_mfcc", settings.audio.n_mfcc, "audio", "MFCC count"),
            value("audio.n_chroma", settings.audio.n_chroma, "audio", "Chroma bins"),
            value("chroma.path", settings.chroma.path, "knowledge", "Knowledge index path"),
            value(
                "chroma.collection",
                settings.chroma.collection,
                "knowledge",
                "Knowledge collection",
            ),
            value(
                "embedding.model_path",
                settings.embedding.model_path,
                "knowledge",
                "Embedding model",
            ),
            value(
                "embedding.device",
                settings.embedding.device,
                "knowledge",
                "Embedding device",
            ),
            value(
                "runtime.report_dir",
                settings.runtime.report_dir,
                "reports",
                "Report directory",
            ),
            value(
                "runtime.model_cache_dir",
                settings.runtime.model_cache_dir,
                "storage",
                "Model cache directory",
            ),
            value("runtime.cache_dir", settings.runtime.cache_dir, "storage", "Cache directory"),
            value("runtime.log_dir", settings.runtime.log_dir, "logging", "Backend log directory"),
            value("logging.level", settings.logging.level, "logging", "Backend log level"),
            value("logging.format", settings.logging.format, "logging", "Backend log format"),
        )
        return SettingsSnapshot(
            revision="packaged-v2",
            source="packaged_default",
            values=values,
            credential_configured=self._credential_configured(settings.llm.api_key),
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
                    source_path=command.source_path,
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
            intelligence=IntelligenceSnapshot(
                engineering=self._engineering_intelligence(getattr(response, "engineering", None)),
                mix=self._mix_intelligence(getattr(response, "mix_intelligence", None)),
                plugin=self._plugin_intelligence(getattr(response, "plugin_intelligence", None)),
                reasoning=self._reasoning_text(command, report),
            ),
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
        reports = self._reference_reports(command.output_directory, command.current_path)
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

    def search_knowledge(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        text = query.text.strip()
        if not text:
            raise ValueError("Knowledge query must not be empty.")
        service = self._knowledge_boundary()
        results = service.search(text)
        return KnowledgeSearchResult(
            query=text,
            items=tuple(
                KnowledgeResultItem(
                    content=str(item.text),
                    source=str(item.source),
                    page=int(item.page),
                    raw_score=float(item.score),
                    raw_rerank_score=float(item.rerank_score),
                )
                for item in results
            ),
        )

    def load_report(self, descriptor: ReportDescriptor) -> ReportPreview:
        self._validate_report_descriptor(descriptor)
        path = descriptor.path
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path)
        stat = path.stat()
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        if stat.st_size > self._MAX_REPORT_PREVIEW_BYTES:
            return ReportPreview(
                descriptor=descriptor,
                content=None,
                size_bytes=stat.st_size,
                filesystem_modified_at=modified_at,
                unavailable_reason="Preview is unavailable because this report exceeds 2 MiB.",
            )

        content = path.read_text(encoding="utf-8")
        warnings: tuple[str, ...] = ()
        if descriptor.format == "json":
            try:
                content = json.dumps(
                    json.loads(content), indent=2, ensure_ascii=False, allow_nan=False
                )
            except (json.JSONDecodeError, ValueError):
                warnings = ("JSON formatting failed; showing the original UTF-8 text.",)
        return ReportPreview(
            descriptor=descriptor,
            content=content,
            size_bytes=stat.st_size,
            filesystem_modified_at=modified_at,
            warnings=warnings,
        )

    def export_report(self, command: ReportExportCommand) -> ReportExportResult:
        source = command.source
        self._validate_report_descriptor(source)
        if not source.path.exists() or not source.path.is_file():
            raise FileNotFoundError(source.path)
        destination = command.destination_path
        expected_extension = self._REPORT_EXTENSIONS[source.format]
        if destination.suffix.casefold() != expected_extension:
            raise ValueError(f"Destination must use {expected_extension}.")
        if not destination.parent.exists() or not destination.parent.is_dir():
            raise FileNotFoundError(destination.parent)
        if destination.exists() and not command.overwrite:
            raise FileExistsError(destination)

        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            shutil.copyfile(source.path, temporary_path)
            if destination.exists() and not command.overwrite:
                raise FileExistsError(destination)
            temporary_path.replace(destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

        exported = ReportDescriptor(
            kind=source.kind,
            format=source.format,
            path=destination,
            display_label=destination.name,
            source_path=source.source_path,
        )
        return ReportExportResult(source=source, exported=exported)

    def _analysis_boundary(self) -> tuple[Any, type[Any]]:
        from phasenox.application.phasenox_service import AnalysisRequest, PhasenoxService

        factory = self._service_factory or PhasenoxService
        return factory(), AnalysisRequest

    def _knowledge_boundary(self) -> Any:
        # Knowledge stays unavailable by default because dependency importability
        # does not prove corpus/model readiness. Tests may inject an explicit,
        # ready application boundary without coupling presentation to RAG internals.
        if self._rag_service_factory is not None:
            return self._rag_service_factory()
        raise RuntimeError("Knowledge search readiness has not been validated.")

    @staticmethod
    def _credential_configured(raw_value: object) -> bool:
        if not isinstance(raw_value, str):
            return False
        normalized = raw_value.strip().casefold()
        placeholders = {
            "",
            "changeme",
            "lm-studio",
            "none",
            "not-set",
            "placeholder",
            "replace-me",
        }
        return normalized not in placeholders

    @classmethod
    def _engineering_intelligence(cls, engineering: Any) -> tuple[IntelligenceItem, ...]:
        items = [
            IntelligenceItem(
                statement_id=f"engineering-strength-{index}",
                source_operation="analysis",
                observation=str(value),
                category="engineering_strength",
                validation_state="freeze_tested",
            )
            for index, value in enumerate(getattr(engineering, "strengths", ()), start=1)
        ]
        items.extend(
            IntelligenceItem(
                statement_id=f"engineering-issue-{index}",
                source_operation="analysis",
                finding=str(issue.title),
                explanations=(str(issue.description),) if issue.description else (),
                recommendation=str(issue.recommendation),
                confidence=float(issue.confidence),
                confidence_meaning="Backend-provided engineering confidence.",
                category="engineering_issue",
                severity=str(issue.severity),
                evidence=(IntelligenceEvidence("severity", str(issue.severity)),),
                validation_state="freeze_tested",
            )
            for index, issue in enumerate(getattr(engineering, "issues", ()), start=1)
        )
        items.extend(
            IntelligenceItem(
                statement_id=f"engineering-recommendation-{index}",
                source_operation="analysis",
                finding=str(recommendation.title),
                explanations=(str(recommendation.reason),) if recommendation.reason else (),
                proposed_action=str(recommendation.action),
                confidence=float(recommendation.confidence),
                confidence_meaning="Backend-provided recommendation confidence.",
                category="engineering_recommendation",
                validation_state="freeze_tested",
            )
            for index, recommendation in enumerate(
                getattr(engineering, "recommendations", ()), start=1
            )
        )
        return tuple(items)

    @staticmethod
    def _reasoning_text(command: AnalysisCommand, report: Any) -> str:
        if not command.include_reasoning:
            return ""
        summary = str(getattr(report, "ai_summary", ""))
        deterministic_baseline = command.intent or command.delivery_target
        return summary if summary and summary != deterministic_baseline else ""

    @classmethod
    def _mix_intelligence(cls, mix: Any) -> tuple[IntelligenceItem, ...]:
        if mix is None:
            return ()
        items = []
        items.extend(
            IntelligenceItem(
                observation=str(cause.symptom),
                explanations=tuple(str(value) for value in cause.likely_causes),
                confidence=float(cause.confidence),
                evidence=(IntelligenceEvidence("priority", str(cause.priority)),),
            )
            for cause in mix.root_causes
        )
        items.extend(
            IntelligenceItem(
                observation=str(issue.description),
                finding=str(issue.title),
                recommendation=str(issue.recommendation),
                confidence=float(issue.confidence),
                evidence=(
                    IntelligenceEvidence("severity", str(issue.severity)),
                    IntelligenceEvidence("category", str(issue.category)),
                    IntelligenceEvidence("priority_score", float(issue.priority_score)),
                    IntelligenceEvidence("user_action_order", int(issue.user_action_order)),
                ),
            )
            for issue in mix.prioritized_issues
        )
        items.extend(
            IntelligenceItem(
                finding=str(step.target),
                recommendation=str(step.suggestion),
                confidence=float(step.confidence),
                evidence=(
                    IntelligenceEvidence("order", int(step.order)),
                    IntelligenceEvidence("plugin_type", str(step.plugin_type)),
                    IntelligenceEvidence("estimated_impact", str(step.estimated_impact)),
                ),
            )
            for step in mix.processing_chain
        )
        items.extend(
            IntelligenceItem(explanations=(str(explanation),)) for explanation in mix.explanations
        )
        return tuple(items)

    @classmethod
    def _plugin_intelligence(cls, plugin: Any) -> tuple[IntelligenceItem, ...]:
        if plugin is None:
            return ()
        items = []
        for step in plugin.steps:
            evidence = [
                IntelligenceEvidence("order", int(step.order)),
                IntelligenceEvidence("target", str(step.goal.target)),
                IntelligenceEvidence("plugin_category", str(step.plugin_category)),
                IntelligenceEvidence("plugin_type", str(step.plugin_type)),
                IntelligenceEvidence("estimated_impact", str(step.estimated_impact)),
            ]
            if step.goal.root_cause:
                evidence.append(IntelligenceEvidence("root_cause", str(step.goal.root_cause)))
            evidence.extend(
                IntelligenceEvidence(
                    "plugin_option",
                    f"{option.brand} {option.name}".strip(),
                )
                for option in step.plugin_options
            )
            parameters = tuple(
                IntelligenceParameter(
                    name=str(parameter.name),
                    value=cls._ui_scalar(parameter.value),
                    unit=(str(parameter.unit) if parameter.unit is not None else None),
                    confidence=float(parameter.confidence),
                    reason=str(parameter.reason),
                    range_min=(
                        float(parameter.range_min)
                        if getattr(parameter, "range_min", None) is not None
                        else None
                    ),
                    range_max=(
                        float(parameter.range_max)
                        if getattr(parameter, "range_max", None) is not None
                        else None
                    ),
                )
                for parameter in step.parameter_recommendations
            )
            items.append(
                IntelligenceItem(
                    observation=str(step.goal.description),
                    finding=str(step.plugin_category),
                    explanations=(str(step.goal.root_cause),) if step.goal.root_cause else (),
                    recommendation=str(step.suggestion),
                    proposed_action=str(step.goal.action),
                    confidence=float(step.confidence),
                    evidence=tuple(evidence),
                    parameters=parameters,
                )
            )
        items.extend(
            IntelligenceItem(explanations=(str(explanation),))
            for explanation in plugin.explanations
        )
        return tuple(items)

    @staticmethod
    def _ui_scalar(value: Any) -> str | int | float | bool | None:
        return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)

    @staticmethod
    def _reference_reports(
        output_directory: Path | None,
        source_path: Path | None = None,
    ) -> tuple[ReportDescriptor, ...]:
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
                        source_path=source_path,
                    )
                )
        return tuple(descriptors)

    @classmethod
    def _validate_report_descriptor(cls, descriptor: ReportDescriptor) -> None:
        formats = cls._REPORT_FORMATS.get(descriptor.kind, frozenset())
        if descriptor.format not in formats:
            raise ValueError("This report type or format is not supported by PHASENOX Desktop.")

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
