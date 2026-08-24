from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from phasenox.resources.branding import APP_ICON, DISPLAY_NAME, WORDMARK_RHYTHM
from phasenox.ui.adapters.v2 import V2ApplicationAdapter
from phasenox.ui.app import build_main_window, create_application
from phasenox.ui.brand_resources import application_icon, brand_asset_bytes
from phasenox.ui.branding import DESKTOP_APPLICATION_ID, default_product_metadata
from phasenox.ui.contracts import Availability, CapabilityLifecycle, CapabilitySnapshot
from phasenox.ui.knowledge_state import KnowledgeQueryState
from phasenox.ui.presentation_state import NAVIGATION_ORDER, PageId
from phasenox.ui.state import ApplicationStateStore


def test_canonical_product_and_desktop_identity() -> None:
    metadata = default_product_metadata()

    assert metadata.display_name == DISPLAY_NAME == "PHASENØX"
    assert metadata.ascii_name == "PHASENOX"
    assert metadata.technical_identity == "PHASENOX"
    assert metadata.application_id == DESKTOP_APPLICATION_ID == "phasenox.desktop"
    assert WORDMARK_RHYTHM == "PHASE   NØX"


def test_approved_brand_bridge_works_outside_repository_cwd(qapp, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert brand_asset_bytes(APP_ICON)
    assert not application_icon().isNull()


def test_shell_constructs_and_closes_offscreen(qtbot, fake_adapter) -> None:
    application = create_application(fake_adapter.product_metadata())
    window = build_main_window(fake_adapter, ApplicationStateStore())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert application.applicationDisplayName() == "Test Product"
    assert window.windowTitle() == "Test Product Desktop"

    window.close()
    assert not window.isVisible()


def test_navigation_exposes_only_truthful_sprint_17b_surfaces() -> None:
    assert NAVIGATION_ORDER == (
        PageId.OVERVIEW,
        PageId.ANALYZE,
        PageId.REFERENCES,
        PageId.INTELLIGENCE,
        PageId.KNOWLEDGE,
        PageId.REPORTS,
        PageId.SETTINGS,
    )
    assert PageId.VOICE not in NAVIGATION_ORDER


def test_knowledge_is_disabled_without_rag_readiness() -> None:
    query = KnowledgeQueryState(text="How should I fix masking?").with_capabilities(
        (
            CapabilitySnapshot(
                id="rag_retrieval",
                display_name="RAG retrieval",
                lifecycle=CapabilityLifecycle.IMPLEMENTED,
                availability=Availability.UNAVAILABLE,
                reason="Corpus and model readiness are not validated.",
                readiness_source="readiness_required",
            ),
        )
    )

    assert not query.can_search
    assert "unavailable" in query.validation_message.casefold()


def test_adapter_capability_truth_never_equates_importability_with_readiness() -> None:
    snapshots = {item.id: item for item in V2ApplicationAdapter().capability_snapshots()}

    assert snapshots["rag_retrieval"].availability is Availability.UNAVAILABLE
    assert snapshots["rag_retrieval"].readiness_source == "readiness_required"
    assert snapshots["audio_intelligence"].availability is Availability.UNAVAILABLE
    assert snapshots["audio_intelligence"].readiness_source == "lifecycle"
    assert all(
        item.availability is not Availability.AVAILABLE
        for item in snapshots.values()
        if item.lifecycle is CapabilityLifecycle.PLANNED
    )


def test_desktop_import_does_not_eagerly_load_heavy_frameworks(tmp_path) -> None:
    repository = Path(__file__).parents[2]
    code = """
import json
import sys
from phasenox.ui.adapters.v2 import V2ApplicationAdapter
from phasenox.ui.app import build_main_window
adapter = V2ApplicationAdapter()
adapter.product_metadata()
adapter.capability_snapshots()
print(json.dumps({name: name in sys.modules for name in (
    'torch', 'transformers', 'onnxruntime', 'chromadb'
)}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(repository)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout.strip()) == {
        "torch": False,
        "transformers": False,
        "onnxruntime": False,
        "chromadb": False,
    }
