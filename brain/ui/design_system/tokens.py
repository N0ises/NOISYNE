"""Qt-free design tokens for temporary neutral desktop branding."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColorTokens:
    background: str = "#111318"
    surface: str = "#181b22"
    surface_raised: str = "#20242d"
    surface_overlay: str = "#292e39"
    text_primary: str = "#f2f4f8"
    text_secondary: str = "#b7bdc9"
    text_muted: str = "#8991a1"
    border: str = "#343a47"
    divider: str = "#2b303b"
    accent: str = "#8ea8ff"
    accent_hover: str = "#a6b9ff"
    accent_pressed: str = "#718ee8"
    accent_text: str = "#10131a"
    success: str = "#5fc995"
    success_surface: str = "#19382b"
    warning: str = "#e2b866"
    warning_surface: str = "#3b301b"
    error: str = "#ef7d86"
    error_surface: str = "#402127"
    info: str = "#72b9e8"
    info_surface: str = "#1c3342"
    focus: str = "#b5c5ff"
    disabled_surface: str = "#242832"
    disabled_text: str = "#666d7a"
    selection: str = "#34466f"


@dataclass(frozen=True, slots=True)
class SpacingTokens:
    xxs: int = 2
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    xxxl: int = 48


@dataclass(frozen=True, slots=True)
class TypographyTokens:
    family: str = "Segoe UI"
    caption_size: int = 11
    body_size: int = 13
    label_size: int = 13
    title_size: int = 18
    page_title_size: int = 24
    metric_size: int = 26
    regular_weight: int = 400
    medium_weight: int = 500
    strong_weight: int = 600


@dataclass(frozen=True, slots=True)
class RadiusTokens:
    small: int = 4
    medium: int = 8
    large: int = 12
    pill: int = 999


@dataclass(frozen=True, slots=True)
class ControlTokens:
    compact_height: int = 28
    standard_height: int = 36
    large_height: int = 44
    minimum_touch_target: int = 32
    sidebar_width: int = 196
    dialog_minimum_width: int = 380
    window_minimum_width: int = 720
    window_minimum_height: int = 500
    window_default_width: int = 960
    window_default_height: int = 640


@dataclass(frozen=True, slots=True)
class IconTokens:
    small: int = 14
    medium: int = 18
    large: int = 24


@dataclass(frozen=True, slots=True)
class InteractionTokens:
    disabled_opacity: float = 0.56
    hover_overlay_alpha: int = 18
    pressed_overlay_alpha: int = 30
    focus_width: int = 2
    border_width: int = 1


@dataclass(frozen=True, slots=True)
class DesignTokens:
    colors: ColorTokens = ColorTokens()
    spacing: SpacingTokens = SpacingTokens()
    typography: TypographyTokens = TypographyTokens()
    radius: RadiusTokens = RadiusTokens()
    controls: ControlTokens = ControlTokens()
    icons: IconTokens = IconTokens()
    interaction: InteractionTokens = InteractionTokens()


DEFAULT_TOKENS = DesignTokens()
