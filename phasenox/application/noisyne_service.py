from __future__ import annotations

import logging
from dataclasses import dataclass, field, is_dataclass, replace
from pathlib import Path
from typing import Any

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext
from phasenox.audio.engineer.models import EngineerResult
from phasenox.audio.io.models import AudioData
from phasenox.audio.mix.chains import ProcessingChainRecommender
from phasenox.audio.mix.explanation import ExplanationBuilder
from phasenox.audio.mix.models import MixIntelligenceResult
from phasenox.audio.mix.priority import PriorityEngine
from phasenox.audio.mix.root_cause import RootCauseAnalyzer
from phasenox.audio.plugin.models import PluginIntelligenceResult
from phasenox.audio.plugin.service import PluginIntelligenceService
from phasenox.reference.models import ReferenceComparison, ReferenceIntent
from phasenox.report.models import SoundBrainReport

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class AnalysisRequest:
    """
    V1 NØISYNE analysis request.

    The deterministic audio review flow is always executed. Optional features
    (reference comparison, LLM reasoning, RAG retrieval, CLAP semantic analysis,
    mix intelligence) are flag-gated and gracefully degrade when disabled or
    unavailable.
    """

    audio_path: str | Path
    reference_path: str | Path | list[str | Path] | None = None
    reference_output_directory: str | Path | None = None
    intent: str = ""
    delivery_target: str = ""
    reference_genre: str | None = None
    reference_mood: str | None = None
    reference_target: str | None = None
    reference_focus: list[str] = field(default_factory=list)
    include_reasoning: bool = False
    include_rag: bool = False
    include_semantic_analysis: bool = False
    include_mix_intelligence: bool = False
    include_plugin_intelligence: bool = False
    output_path: str | Path | None = None


@dataclass(slots=True)
class AnalysisResponse:
    """
    V1 NØISYNE analysis response.

    Contains the full deterministic pipeline output plus any optional results
    that were successfully produced (e.g. reference comparison, mix intelligence).
    """

    audio: AudioData
    analysis: AnalysisResult
    context: AudioContext
    engineering: EngineerResult
    report: SoundBrainReport
    comparison: ReferenceComparison | None = None
    mix_intelligence: MixIntelligenceResult | None = None
    plugin_intelligence: PluginIntelligenceResult | None = None
    status: str = "ok"
    warnings: list[str] = field(default_factory=list)


class NoisyneService:
    """
    Single entry point for the V1 NØISYNE workflow.

    The service composes the deterministic ``AudioReviewService`` and optionally
    the ``ReferencePipeline``. Heavy modules are imported inside methods so that
    importing this module does not load torch, transformers, or audio models.

    The legacy ``SoundBrainService`` name remains available as a compatibility
    alias from ``phasenox.application.soundbrain_service``.
    """

    def __init__(
        self,
        *,
        audio_review_service: Any | None = None,
        reference_pipeline: Any | None = None,
        plugin_intelligence_service: PluginIntelligenceService | None = None,
    ) -> None:
        self._audio_review_service = audio_review_service
        self._reference_pipeline = reference_pipeline
        self._plugin_intelligence_service = plugin_intelligence_service

    def analyze(
        self,
        request: AnalysisRequest,
    ) -> AnalysisResponse:
        """
        Run the V1 NØISYNE analysis workflow.

        Optional stages are executed only when explicitly requested and only when
        their dependencies are available. A missing optional stage never breaks
        the deterministic report.
        """
        from phasenox.application.audio_review_service import (
            AudioReviewRequest,
            AudioReviewService,
        )

        review_service = self._audio_review_service or AudioReviewService()

        review_request = AudioReviewRequest(
            audio_path=request.audio_path,
            include_semantic_analysis=request.include_semantic_analysis,
            summary=request.intent or request.delivery_target or "",
            output_path=request.output_path,
        )
        review_result = review_service.review(review_request)

        warnings: list[str] = []

        comparison = self._run_reference_comparison(request, warnings)

        rag_context = ""
        if request.include_rag:
            rag_context = self._run_rag_retrieval(
                review_result.context,
                review_result.engineering,
                request,
                warnings,
            )

        report = review_result.report
        mix_result: MixIntelligenceResult | None = None
        plugin_result: PluginIntelligenceResult | None = None
        if request.include_mix_intelligence:
            mix_result = self._run_mix_intelligence(review_result, warnings)
            if mix_result is not None:
                report = self._enrich_report_with_mix(report, mix_result)

        if request.include_plugin_intelligence and mix_result is not None:
            plugin_result = self._run_plugin_intelligence(
                mix_result,
                review_result.context,
                warnings,
            )
            if plugin_result is not None:
                report = self._enrich_report_with_plugin(report, plugin_result)

        if request.include_reasoning:
            reference_summary = ""
            if comparison is not None:
                reference_summary = self._format_reference_summary(comparison)
            mix_summary = ""
            if mix_result is not None:
                mix_summary = self._format_mix_summary(mix_result)
            reasoning_answer = self._run_reasoning(
                review_result=review_result,
                rag_context=rag_context,
                reference_summary=reference_summary,
                mix_summary=mix_summary,
                request=request,
                warnings=warnings,
            )
            if reasoning_answer:
                report = self._rebuild_report_with_reasoning(
                    report=report,
                    ai_answer=reasoning_answer,
                )

        status = "ok" if not warnings else "degraded"

        if is_dataclass(report) and not isinstance(report, type):
            report = replace(report, status=status, warnings=warnings)

        if request.output_path is not None and review_result.report is not report:
            from phasenox.report import ReportExporter

            ReportExporter().save_json(report, str(request.output_path))

        return AnalysisResponse(
            audio=review_result.audio,
            analysis=review_result.analysis,
            context=review_result.context,
            engineering=review_result.engineering,
            report=report,
            comparison=comparison,
            mix_intelligence=mix_result,
            plugin_intelligence=plugin_result,
            status=status,
            warnings=warnings,
        )

    def _run_reference_comparison(
        self,
        request: AnalysisRequest,
        warnings: list[str],
    ) -> ReferenceComparison | None:
        """
        Run the reference comparison pipeline when a reference path is provided.

        Supports a single reference or a list of references. Returns ``None`` if
        no reference path is supplied or if the comparison fails. This keeps the
        deterministic report intact.
        """
        if request.reference_path is None:
            return None

        try:
            from phasenox.reference.pipeline import ReferencePipeline

            pipeline = self._reference_pipeline or ReferencePipeline()

            intent = ReferenceIntent(
                genre=request.reference_genre,
                mood=request.reference_mood,
                target=(request.reference_target or request.delivery_target or None),
                focus_areas=request.reference_focus,
            )

            report = pipeline.run(
                reference_audio=request.reference_path,
                current_audio=request.audio_path,
                output_directory=request.reference_output_directory,
                intent=intent,
            )
            return report.comparison
        except Exception as exc:
            message = f"Reference comparison failed: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return None

    def _format_reference_summary(
        self,
        comparison: ReferenceComparison,
    ) -> str:
        """Format a short reference comparison summary for reasoning context."""

        parts = [
            "Reference comparison summary:",
            f"  Overall similarity: {comparison.similarity:.2f}%",
        ]

        if comparison.reference_similarities:
            parts.append("  Per-reference similarity:")
            for path, similarity in comparison.reference_similarities.items():
                parts.append(f"    - {Path(path).name}: {similarity:.2f}%")

        if comparison.metric_variance:
            parts.append("  High-variance metrics:")
            for metric, value in comparison.metric_variance.items():
                if value > 0.01:
                    parts.append(f"    - {metric}: {value:.4f}")

        if comparison.segment_deviations:
            parts.append("  Key deviations:")
            for seg in comparison.segment_deviations[:5]:
                parts.append(
                    f"    - {seg.start_time:.1f}s-{seg.end_time:.1f}s "
                    f"{seg.metric}: Δ={seg.current_value - seg.reference_value:.2f}"
                )

        return "\n".join(parts)

    def _run_rag_retrieval(
        self,
        context: AudioContext,
        engineering: EngineerResult,
        request: AnalysisRequest,
        warnings: list[str],
    ) -> str:
        """
        Retrieve relevant documents from the RAG collection.

        Returns a formatted context string, or an empty string if retrieval is
        unavailable or fails. This never breaks the deterministic report.
        """
        try:
            from phasenox.rag.retriever import retrieve
        except Exception as exc:
            message = f"RAG retriever unavailable: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return ""

        query_parts = [request.intent, request.delivery_target, context.audio_type]
        query_parts.extend(issue.title for issue in engineering.issues)
        query = " ".join(part for part in query_parts if part).strip()

        if not query:
            logger.debug("RAG query is empty; skipping retrieval.")
            return ""

        try:
            documents = retrieve(query, k=5)
        except Exception as exc:
            message = f"RAG retrieval failed: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return ""

        if not documents:
            logger.debug("RAG retrieval returned no documents.")
            return ""

        formatted = ["Retrieved knowledge:"]
        for doc in documents[:5]:
            source = doc.get("source", "unknown")
            text = doc.get("text", "").strip()
            if text:
                formatted.append(f"- [{source}] {text}")

        return "\n".join(formatted)

    def _run_reasoning(
        self,
        *,
        review_result: Any,
        rag_context: str,
        reference_summary: str,
        mix_summary: str = "",
        request: AnalysisRequest,
        warnings: list[str],
    ) -> str:
        """
        Run LLM reasoning over the deterministic results.

        Returns the LLM answer as a string, or an empty string if reasoning fails
        or is unavailable.
        """
        try:
            from phasenox.reasoning.engine import ReasoningEngine
            from phasenox.reasoning.models import ReasoningContext
        except Exception as exc:
            message = f"Reasoning engine unavailable: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return ""

        question_parts = [request.intent, request.delivery_target]
        if reference_summary:
            question_parts.append(reference_summary)
        if mix_summary:
            question_parts.append(mix_summary)
        if rag_context:
            question_parts.append(rag_context)
        question = "\n\n".join(part for part in question_parts if part).strip()

        if not question:
            question = "Provide an engineering summary of the audio analysis."

        try:
            engine = ReasoningEngine()
            result = engine.ask(
                ReasoningContext(
                    analysis=review_result.analysis,
                    engineer=review_result.engineering,
                    audio_context=review_result.context,
                    question=question,
                )
            )
        except Exception as exc:
            message = f"Reasoning failed: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return ""

        if not result.answer:
            return ""

        return result.answer

    def _rebuild_report_with_reasoning(
        self,
        *,
        report: SoundBrainReport,
        ai_answer: str,
    ) -> SoundBrainReport:
        """
        Rebuild the report with the LLM-generated summary.

        All deterministic fields — including optional mix intelligence — are
        preserved; only ``ai_summary`` is updated.
        """
        return replace(report, ai_summary=ai_answer)

    def _run_mix_intelligence(
        self,
        review_result: Any,
        warnings: list[str],
    ) -> MixIntelligenceResult | None:
        """
        Run deterministic mix intelligence over the deterministic results.

        Returns ``None`` if the heuristic analysis fails, so the deterministic
        report is still delivered.
        """
        try:
            root_causes = RootCauseAnalyzer().analyze(
                review_result.analysis,
                review_result.context,
                review_result.engineering,
            )
            prioritized = PriorityEngine().prioritize(
                review_result.engineering,
                root_causes,
            )
            chain = ProcessingChainRecommender().recommend(
                root_causes,
                prioritized,
                review_result.context,
            )
            explanations = ExplanationBuilder().build(
                review_result.analysis,
                review_result.context,
                review_result.engineering,
                root_causes.causes,
                chain,
            )

            return MixIntelligenceResult(
                root_causes=root_causes.causes,
                prioritized_issues=prioritized,
                processing_chain=chain,
                explanations=explanations,
                confidence_scores=root_causes.confidence_scores,
            )
        except Exception as exc:
            message = f"Mix intelligence failed: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return None

    def _enrich_report_with_mix(
        self,
        report: SoundBrainReport,
        mix_result: MixIntelligenceResult,
    ) -> SoundBrainReport:
        """Attach deterministic mix intelligence fields to the report."""
        return replace(
            report,
            root_causes=mix_result.root_causes,
            prioritized_issues=mix_result.prioritized_issues,
            processing_chain=mix_result.processing_chain,
            explanations=mix_result.explanations,
            confidence_scores=mix_result.confidence_scores,
        )

    def _format_mix_summary(
        self,
        mix_result: MixIntelligenceResult,
    ) -> str:
        """Format a short mix intelligence summary for reasoning context."""
        parts = ["Mix intelligence summary:"]

        if mix_result.prioritized_issues:
            parts.append("  Prioritized issues:")
            for issue in mix_result.prioritized_issues[:5]:
                parts.append(
                    f"    - {issue.user_action_order}. {issue.title} "
                    f"({issue.severity}, score={issue.priority_score:.2f})"
                )

        if mix_result.root_causes:
            parts.append("  Root causes:")
            for cause in mix_result.root_causes[:5]:
                parts.append(f"    - {cause.symptom}: {', '.join(cause.likely_causes)}")

        if mix_result.processing_chain:
            parts.append("  Suggested processing chain:")
            for step in mix_result.processing_chain[:5]:
                parts.append(
                    f"    - Step {step.order}: {step.plugin_type} on {step.target} "
                    f"({step.estimated_impact} impact)"
                )

        return "\n".join(parts)

    def _run_plugin_intelligence(
        self,
        mix_result: MixIntelligenceResult,
        context: AudioContext,
        warnings: list[str],
    ) -> PluginIntelligenceResult | None:
        """
        Run deterministic plugin intelligence over the Mix Intelligence result.

        Returns ``None`` if plugin intelligence fails, so the report still contains
        the Mix Intelligence output.
        """
        try:
            service = self._plugin_intelligence_service or PluginIntelligenceService()
            return service.analyze(mix_result, context)
        except Exception as exc:
            message = f"Plugin intelligence failed: {exc}"
            logger.warning(
                message,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            warnings.append(message)
            return None

    def _enrich_report_with_plugin(
        self,
        report: SoundBrainReport,
        plugin_result: PluginIntelligenceResult,
    ) -> SoundBrainReport:
        """Attach deterministic plugin intelligence fields to the report."""
        return replace(report, plugin_intelligence=plugin_result)
