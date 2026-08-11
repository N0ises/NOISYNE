from __future__ import annotations


from .models import (
    SoundBrainReport,
    ReportIssue,
)


from .validator import (
    ReportValidator,
)



class ReportBuilder:



    def build(
        self,
        analysis,
        engineer,
        audio_context,
        ai_answer: str,
        analysis_dict: dict | None = None,
    ) -> SoundBrainReport:



        semantic = []



        for label in audio_context.semantic_labels:


            semantic.append(

                f"{label.name}: {label.confidence:.2f}"

            )



        issues = []



        for issue in engineer.issues:


            issues.append(

                ReportIssue(

                    title=issue.title,

                    severity=issue.severity,

                    description=issue.description,

                    recommendation=issue.recommendation,

                    confidence=issue.confidence,

                )

            )



        recommendations = []



        for issue in engineer.issues:


            recommendations.append(

                issue.recommendation

            )



        validated_summary = ReportValidator().validate(

            ai_answer

        )



        return SoundBrainReport(


            audio_type=audio_context.audio_type,


            source_type=audio_context.source_type,


            instrument=audio_context.instrument,


            is_full_mix=audio_context.is_full_mix,


            confidence=audio_context.confidence,


            semantic_labels=semantic,


            score=engineer.score,


            strengths=list(

                engineer.strengths

            ),


            issues=issues,


            recommendations=recommendations,


            ai_summary=validated_summary,


            analysis=analysis_dict,


        )