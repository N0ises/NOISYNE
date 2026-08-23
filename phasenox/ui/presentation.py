"""Qt-free view projection for the desktop shell."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ProductMetadata
from .presentation_state import NAVIGATION_ORDER, NavigationState, PageId


@dataclass(frozen=True, slots=True)
class NavigationItem:
    page_id: PageId
    label: str


_PAGE_LABELS = {
    PageId.OVERVIEW: "Overview",
    PageId.ANALYZE: "Analyze",
    PageId.REFERENCES: "References",
    PageId.INTELLIGENCE: "Intelligence",
    PageId.VOICE: "Voice / Agent",
    PageId.KNOWLEDGE: "Knowledge",
    PageId.REPORTS: "Reports",
    PageId.SETTINGS: "Settings",
    PageId.RUNTIME_STATUS: "Runtime / Status",
}


@dataclass(frozen=True, slots=True)
class ShellViewState:
    metadata: ProductMetadata
    window_title: str
    heading: str
    body: str
    navigation_items: tuple[NavigationItem, ...]
    status_message: str


def build_shell_view_state(
    metadata: ProductMetadata, navigation: NavigationState | None = None
) -> ShellViewState:
    available = navigation.available_pages if navigation is not None else NAVIGATION_ORDER
    return ShellViewState(
        metadata=metadata,
        window_title=metadata.application_title,
        heading=metadata.display_name,
        body="Desktop foundation is ready.",
        navigation_items=tuple(NavigationItem(page, _PAGE_LABELS[page]) for page in available),
        status_message="Ready",
    )

