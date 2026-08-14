from __future__ import annotations

import json
import re

from .models import (
    AudioFact,
    EngineeringFinding,
    ReasoningRecommendation,
    ReasoningResult,
    StructuredReasoningResponse,
)


class ResponseParser:
    """
    Parses LLM structured responses.

    Supports JSON output with fallback
    to raw text.
    """

    def parse(
        self,
        text: str,
    ) -> ReasoningResult:

        cleaned = self._clean_json(text)

        try:

            data = json.loads(cleaned)

            structured = self._parse_json(data)

            return ReasoningResult(
                answer=self._render(structured),
                confidence=1.0,
                reasoning=["Structured JSON response parsed."],
                structured=structured,
            )

        except (json.JSONDecodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
            return ReasoningResult(
                answer=text.strip(),
                confidence=1.0,
                reasoning=[
                    "Fallback raw text response.",
                    f"Parsing error: {exc}",
                ],
            )

    def _clean_json(
        self,
        text: str,
    ) -> str:

        cleaned = text.strip()

        cleaned = re.sub(
            r"^```json\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"^```\s*",
            "",
            cleaned,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        return cleaned.strip()

    def _parse_json(
        self,
        data: dict,
    ) -> StructuredReasoningResponse:

        facts = [
            AudioFact(
                name=item.get(
                    "name",
                    "",
                ),
                value=item.get(
                    "value",
                    "",
                ),
            )
            for item in data.get(
                "facts",
                [],
            )
        ]

        findings = [
            EngineeringFinding(
                title=item.get(
                    "title",
                    "",
                ),
                severity=item.get(
                    "severity",
                    "",
                ),
                description=item.get(
                    "description",
                    "",
                ),
                recommendation=item.get(
                    "recommendation",
                    "",
                ),
            )
            for item in data.get(
                "findings",
                [],
            )
        ]

        recommendations = [
            ReasoningRecommendation(
                text=item.get(
                    "text",
                    "",
                )
            )
            for item in data.get(
                "recommendations",
                [],
            )
        ]

        return StructuredReasoningResponse(
            facts=facts,
            findings=findings,
            recommendations=recommendations,
            conclusion=data.get(
                "conclusion",
                "",
            ),
        )

    def _render(
        self,
        response: StructuredReasoningResponse,
    ) -> str:

        lines = []

        lines.append("### Audio Facts")

        for fact in response.facts:

            lines.append(f"- {fact.name}: {fact.value}")

        lines.append("")

        lines.append("### Engineering Interpretation")

        for finding in response.findings:

            lines.append(f"- {finding.title} ({finding.severity})")

            lines.append(f"  Description: {finding.description}")

            if finding.recommendation:

                lines.append(f"  Recommendation: {finding.recommendation}")

        lines.append("")

        lines.append("### Recommendations")

        for item in response.recommendations:

            lines.append(f"- {item.text}")

        lines.append("")

        lines.append("### Conclusion")

        # جلوگیری از تفسیر آزاد LLM
        if response.findings:

            issue_titles = ", ".join([item.title for item in response.findings])

            lines.append(
                f"Analysis completed using provided measurements. "
                f"Engineer findings detected: {issue_titles}."
            )

        else:

            lines.append("No engineer findings were detected.")

        return "\n".join(lines)
