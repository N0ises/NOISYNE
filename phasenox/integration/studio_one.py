from __future__ import annotations

from phasenox.integration.base import BaseWorkflowAdapter
from phasenox.integration.models import DAWCapability


class StudioOneAdapter(BaseWorkflowAdapter):
    """Placeholder contract adapter for PreSonus Studio One."""

    name = "studio_one"

    def capabilities(self) -> list[DAWCapability]:
        return [
            DAWCapability(
                "analysis_import",
                "Import analysis summary as song notes",
                available=False,
            ),
            DAWCapability(
                "processing_chain",
                "Export console/processing chain notes as text",
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
