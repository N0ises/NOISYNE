from __future__ import annotations

from phasenox.integration.base import BaseWorkflowAdapter
from phasenox.integration.models import DAWCapability


class CubaseAdapter(BaseWorkflowAdapter):
    """Placeholder contract adapter for Steinberg Cubase."""

    name = "cubase"

    def capabilities(self) -> list[DAWCapability]:
        return [
            DAWCapability(
                "analysis_import",
                "Import analysis summary as track notepad entries",
                available=False,
            ),
            DAWCapability(
                "processing_chain",
                "Export processing chain as channel-strip notes",
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
