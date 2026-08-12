"""Qt-free presentation state for the Sprint 1 shell."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import ProductMetadata


@dataclass(frozen=True, slots=True)
class ShellViewState:
    window_title: str
    heading: str
    body: str
    navigation_items: tuple[str, ...]
    status_message: str


def build_shell_view_state(metadata: ProductMetadata) -> ShellViewState:
    return ShellViewState(
        window_title=metadata.application_title,
        heading=metadata.display_name,
        body="Desktop foundation is ready.",
        navigation_items=("Home",),
        status_message="Ready",
    )
