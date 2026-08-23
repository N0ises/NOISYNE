from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from phasenox.ui.contracts import (
    AnalysisCommand,
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    ProductMetadata,
    ProviderStatus,
    RuntimeState,
    RuntimeStatus,
    SettingsSnapshot,
)


class FakeApplicationAdapter:
    def __init__(self, metadata: ProductMetadata) -> None:
        self._metadata = metadata

    def product_metadata(self) -> ProductMetadata:
        return self._metadata

    def capability_snapshots(self) -> tuple[CapabilitySnapshot, ...]:
        return (
            CapabilitySnapshot(
                id="test",
                display_name="Test capability",
                lifecycle=CapabilityLifecycle.PRODUCTION,
                availability=Availability.AVAILABLE,
            ),
        )

    def runtime_status(self) -> RuntimeStatus:
        return RuntimeStatus(
            state=RuntimeState.READY,
            requested_device="cpu",
            effective_device="cpu",
            device_reason=None,
            loaded_models=(),
            provider=ProviderStatus("fake", Availability.AVAILABLE),
            paths=(),
            configuration_source="test",
            capabilities=self.capability_snapshots(),
            checked_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )

    def settings_snapshot(self) -> SettingsSnapshot:
        return SettingsSnapshot("test", "test", (), False)

    def analyze(self, command: AnalysisCommand) -> AnalysisViewResult:
        return AnalysisViewResult(
            source_path=command.source_path,
            status="ok",
            audio_type="test",
            score=100.0,
            summary="",
        )


@pytest.fixture
def product_metadata() -> ProductMetadata:
    return ProductMetadata(
        display_name="Test Product",
        application_title="Test Product Desktop",
        version="1.2.3",
        organization_name="Test Vendor",
        organization_domain="example.test",
        application_id="test.desktop",
    )


@pytest.fixture
def fake_adapter(product_metadata: ProductMetadata) -> FakeApplicationAdapter:
    return FakeApplicationAdapter(product_metadata)

