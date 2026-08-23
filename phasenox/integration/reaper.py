from __future__ import annotations

from phasenox.integration.base import BaseWorkflowAdapter
from phasenox.integration.models import DAWCapability


class ReaperAdapter(BaseWorkflowAdapter):
    """Placeholder contract adapter for REAPER."""

    name = "reaper"

    def capabilities(self) -> list[DAWCapability]:
        return [
            DAWCapability(
                "analysis_import",
                "Import analysis markers as project metadata",
                available=False,
            ),
            DAWCapability(
                "processing_chain",
                "Export FX chain recommendation as text",
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
