"""Qt-free query and capability state for the Knowledge workspace."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .contracts import Availability, CapabilityLifecycle, CapabilitySnapshot, KnowledgeQuery


@dataclass(frozen=True, slots=True)
class KnowledgeCapabilityState:
    lifecycle: CapabilityLifecycle | None = None
    availability: Availability = Availability.UNKNOWN
    reason: str = "Capability status has not been reported."

    @property
    def executable(self) -> bool:
        return (
            self.lifecycle is not None
            and self.lifecycle is not CapabilityLifecycle.PLANNED
            and self.availability in {Availability.AVAILABLE, Availability.DEGRADED}
        )


@dataclass(frozen=True, slots=True)
class KnowledgeQueryState:
    text: str = ""
    capability: KnowledgeCapabilityState = KnowledgeCapabilityState()
    validation_message: str = "Enter a query to search knowledge."

    def with_capabilities(
        self, capabilities: tuple[CapabilitySnapshot, ...]
    ) -> KnowledgeQueryState:
        capability = next((item for item in capabilities if item.id == "rag_retrieval"), None)
        if capability is None:
            state = KnowledgeCapabilityState()
        else:
            state = KnowledgeCapabilityState(
                lifecycle=capability.lifecycle,
                availability=capability.availability,
                reason=capability.reason or "No availability reason was supplied.",
            )
        return replace(self, capability=state).validate()

    def set_text(self, text: str) -> KnowledgeQueryState:
        return replace(self, text=text).validate()

    def validate(self) -> KnowledgeQueryState:
        if not self.text.strip():
            return replace(self, validation_message="Enter a query to search knowledge.")
        if not self.capability.executable:
            return replace(
                self,
                validation_message=(
                    "Knowledge search is unavailable. " + self.capability.reason
                ).strip(),
            )
        return replace(self, validation_message="Ready to search.")

    @property
    def can_search(self) -> bool:
        return bool(self.text.strip()) and self.capability.executable

    def build_query(self) -> KnowledgeQuery:
        validated = self.validate()
        if not validated.can_search:
            raise ValueError(validated.validation_message)
        return KnowledgeQuery(text=validated.text.strip())
