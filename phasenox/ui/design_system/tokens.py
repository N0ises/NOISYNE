"""Qt-free NØISYNE design tokens mapped from the approved brand package."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColorTokens:
    background: str = "#0A0A0A"
    surface: str = "#141414"
    surface_raised: str = "#1E1E1E"
    surface_overlay: str = "#262626"
    text_primary: str = "#EDEDED"
    text_secondary: str = "#A3A3A3"
    text_muted: str = "#737373"
    border: str = "#2E2E2E"
    divider: str = "#1F1F1F"
    border_strong: str = "#404040"
    accent: str = "#6366F1"
    accent_hover: str = "#818CF8"
    accent_pressed: str = "#4F46E5"
    accent_text: str = "#EDEDED"
    success: str = "#10B981"
    success_surface: str = "#062A20"
    warning: str = "#F59E0B"
    warning_surface: str = "#352300"
    error: str = "#EF4444"
    error_surface: str = "#351111"
    info: str = "#3B82F6"
    info_surface: str = "#081A35"
    unavailable: str = "#525252"
    unknown: str = "#8B5CF6"
    unknown_surface: str = "#251449"
    running: str = "#3B82F6"
    degraded: str = "#F97316"
    degraded_surface: str = "#381704"
    intelligence: str = "#6366F1"
    intelligence_surface: str = "#1B1C46"
    focus: str = "#8B5CF6"
    disabled_surface: str = "#1E1E1E"
    disabled_text: str = "#525252"
    selection: str = "#282950"


@dataclass(frozen=True, slots=True)
class SpacingTokens:
    xxs: int = 2
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 40
    xxxl: int = 48


@dataclass(frozen=True, slots=True)
class TypographyTokens:
    family: str = '"Geist", "Segoe UI", sans-serif'
    mono_family: str = '"Geist Mono", "Consolas", monospace'
    caption_size: int = 12
    body_size: int = 14
    label_size: int = 14
    title_size: int = 20
    page_title_size: int = 24
    metric_size: int = 26
    regular_weight: int = 400
    medium_weight: int = 500
    strong_weight: int = 600


@dataclass(frozen=True, slots=True)
class RadiusTokens:
    small: int = 4
    medium: int = 6
    large: int = 8
    pill: int = 999


@dataclass(frozen=True, slots=True)
class ControlTokens:
    compact_height: int = 24
    standard_height: int = 32
    large_height: int = 40
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

