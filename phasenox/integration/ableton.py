from __future__ import annotations

from phasenox.integration.base import BaseWorkflowAdapter
from phasenox.integration.models import DAWCapability


class AbletonAdapter(BaseWorkflowAdapter):
    """Placeholder contract adapter for Ableton Live."""

    name = "ableton"

    def capabilities(self) -> list[DAWCapability]:
        return [
            DAWCapability(
                "analysis_import",
                "Import analysis summary as session notes",
                available=False,
            ),
            DAWCapability(
                "processing_chain",
                "Export processing chain as text track notes",
                available=True,
            ),
            DAWCapability(
                "plugin_recommendations",
                "Export plugin recommendations as JSON metadata",
                available=True,
            ),
            DAWCapability(
                "report_export",
                "Export full report as Markdown and JSON",
                available=True,
            ),
        ]
