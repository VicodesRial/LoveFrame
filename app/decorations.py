"""Cached, integer-grid pixel-art decorations for the LoveFrame display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

import pygame

from app.config import AppConfig, hex_color_to_rgb

Color = Tuple[int, int, int]
Point = Tuple[int, int]

MEDIUM_HEART_PATTERN = (
    ".MM..MM.",
    "MHHMMMMM",
    "MMMMMMMM",
    ".MMMMMM.",
    "..MMMM..",
    "...MM...",
)
SMALL_HEART_PATTERN = (
    ".M.M.",
    "MHHMM",
    ".MMM.",
    "..M..",
)
SPARKLE_PATTERN = (
    "..S..",
    "..S..",
    "SSSSS",
    "..S..",
    "..S..",
)
OUTLINED_HEART_PATTERN = (
    ".HH..MM.",
    "M..MM..M",
    "M......M",
    ".M....M.",
    "..M..M..",
    "...MM...",
)
DIAMOND_PATTERN = (
    ".D.",
    "DDD",
    ".D.",
)
DOTTED_TRAIL_PATTERN = ("T.T.T",)
PULSE_FRAME_SECONDS = 1.25
PULSE_FRAME_COUNT = 3
REFERENCE_BAR_AREA_RATIO = 0.16


class MotifAnchor(NamedTuple):
    kind: str
    x: float
    y: float
    size: str


VERTICAL_LEFT_TEMPLATE = (
    MotifAnchor("large_heart", 0.34, 0.13, "large"),
    MotifAnchor("heart", 0.68, 0.58, "medium"),
    MotifAnchor("sparkle", 0.70, 0.29, "small"),
    MotifAnchor("small_heart", 0.30, 0.82, "small"),
    MotifAnchor("outline_heart", 0.38, 0.38, "small"),
    MotifAnchor("small_heart", 0.30, 0.49, "small"),
    MotifAnchor("diamond", 0.28, 0.72, "small"),
    MotifAnchor("trail", 0.34, 0.66, "small"),
    MotifAnchor("sparkle", 0.30, 0.92, "small"),
)
VERTICAL_RIGHT_TEMPLATE = (
    MotifAnchor("heart", 0.66, 0.10, "medium"),
    MotifAnchor("heart", 0.30, 0.54, "medium"),
    MotifAnchor("diamond", 0.28, 0.23, "small"),
    MotifAnchor("small_heart", 0.70, 0.78, "small"),
    MotifAnchor("sparkle", 0.72, 0.36, "small"),
    MotifAnchor("small_heart", 0.72, 0.47, "small"),
    MotifAnchor("trail", 0.68, 0.69, "small"),
    MotifAnchor("outline_heart", 0.66, 0.88, "small"),
    MotifAnchor("sparkle", 0.70, 0.94, "small"),
)
VERTICAL_LEFT_HIGH = (
    MotifAnchor("outline_heart", 0.72, 0.43, "small"),
    MotifAnchor("diamond", 0.68, 0.53, "small"),
    MotifAnchor("sparkle", 0.30, 0.76, "small"),
)
VERTICAL_RIGHT_HIGH = (
    MotifAnchor("diamond", 0.30, 0.84, "small"),
    MotifAnchor("outline_heart", 0.28, 0.62, "small"),
    MotifAnchor("sparkle", 0.70, 0.73, "small"),
)
HORIZONTAL_TOP_TEMPLATE = (
    MotifAnchor("large_heart", 0.10, 0.48, "large"),
    MotifAnchor("heart", 0.61, 0.62, "medium"),
    MotifAnchor("sparkle", 0.24, 0.27, "small"),
    MotifAnchor("small_heart", 0.88, 0.35, "small"),
    MotifAnchor("outline_heart", 0.37, 0.72, "small"),
    MotifAnchor("small_heart", 0.68, 0.30, "small"),
    MotifAnchor("diamond", 0.76, 0.74, "small"),
    MotifAnchor("trail", 0.49, 0.25, "small"),
    MotifAnchor("sparkle", 0.94, 0.74, "small"),
)
HORIZONTAL_BOTTOM_TEMPLATE = (
    MotifAnchor("heart", 0.08, 0.20, "medium"),
    MotifAnchor("heart", 0.92, 0.35, "medium"),
    MotifAnchor("diamond", 0.14, 0.55, "small"),
    MotifAnchor("small_heart", 0.86, 0.67, "small"),
    MotifAnchor("sparkle", 0.06, 0.80, "small"),
    MotifAnchor("small_heart", 0.94, 0.86, "small"),
    MotifAnchor("trail", 0.94, 0.55, "small"),
    MotifAnchor("outline_heart", 0.12, 0.36, "small"),
    MotifAnchor("sparkle", 0.88, 0.16, "small"),
)
HORIZONTAL_TOP_HIGH = (
    MotifAnchor("diamond", 0.17, 0.78, "small"),
    MotifAnchor("outline_heart", 0.56, 0.80, "small"),
    MotifAnchor("sparkle", 0.82, 0.46, "small"),
)
HORIZONTAL_BOTTOM_HIGH = (
    MotifAnchor("outline_heart", 0.04, 0.47, "small"),
    MotifAnchor("diamond", 0.96, 0.25, "small"),
    MotifAnchor("sparkle", 0.17, 0.72, "small"),
)


def _draw_pattern(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    pattern: Sequence[str],
    colors: Dict[str, Color],
) -> Tuple[pygame.Rect, ...]:
    if scale <= 0:
        raise ValueError("pixel scale must be positive")

    rectangles = []
    for row, line in enumerate(pattern):
        for column, symbol in enumerate(line):
            if symbol == ".":
                continue
            rectangle = pygame.Rect(
                origin[0] + column * scale,
                origin[1] + row * scale,
                scale,
                scale,
            )
            pygame.draw.rect(surface, colors[symbol], rectangle)
            rectangles.append(rectangle)
    return tuple(rectangles)


def draw_pixel_heart(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    heart_color: Color,
    highlight_color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw one medium heart from crisp, non-antialiased pixel rectangles."""

    return _draw_pattern(
        surface,
        origin,
        scale,
        MEDIUM_HEART_PATTERN,
        {"M": heart_color, "H": highlight_color},
    )


def draw_small_pixel_heart(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    heart_color: Color,
    highlight_color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw one compact heart from crisp, non-antialiased pixel rectangles."""

    return _draw_pattern(
        surface,
        origin,
        scale,
        SMALL_HEART_PATTERN,
        {"M": heart_color, "H": highlight_color},
    )


def draw_four_point_sparkle(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    sparkle_color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw one four-point sparkle from crisp, non-antialiased rectangles."""

    return _draw_pattern(
        surface,
        origin,
        scale,
        SPARKLE_PATTERN,
        {"S": sparkle_color},
    )


def draw_outlined_pixel_heart(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    heart_color: Color,
    highlight_color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw one open-center pixel heart."""

    return _draw_pattern(
        surface,
        origin,
        scale,
        OUTLINED_HEART_PATTERN,
        {"M": heart_color, "H": highlight_color},
    )


def draw_tiny_pixel_diamond(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw one compact filled pixel diamond."""

    return _draw_pattern(surface, origin, scale, DIAMOND_PATTERN, {"D": color})


def draw_dotted_pixel_trail(
    surface: pygame.Surface,
    origin: Point,
    scale: int,
    color: Color,
) -> Tuple[pygame.Rect, ...]:
    """Draw a subtle horizontal trail of three separated pixels."""

    return _draw_pattern(surface, origin, scale, DOTTED_TRAIL_PATTERN, {"T": color})


@dataclass(frozen=True)
class DecorationPlacement:
    """One cached decoration anchored by its center point."""

    kind: str
    center: Point
    scale: int


class PixelDecorationRenderer:
    """Cache pixel-art frames and safely position them around the photo and card."""

    def __init__(self, display_size: Tuple[int, int], config: AppConfig) -> None:
        self.display_size = display_size
        self.show = config.show_decorations
        self.animate = config.animate_decorations
        self.density = config.decoration_density
        self.heart_color = hex_color_to_rgb(config.heart_color)
        self.highlight_color = hex_color_to_rgb(config.heart_highlight_color)
        self.sparkle_color = hex_color_to_rgb(config.sparkle_color)
        background_color = hex_color_to_rgb(config.photo_background_color)
        self.soft_accent_color = tuple(
            round((background_component * 2 + accent_component) / 3)
            for background_component, accent_component in zip(
                background_color,
                self.sparkle_color,
            )
        )
        self.placements: Tuple[DecorationPlacement, ...] = ()
        self._surface_cache: Dict[
            Tuple[str, int, int, Color, Color],
            pygame.Surface,
        ] = {}
        self._render_frames: Tuple[Tuple[Tuple[pygame.Surface, Point], ...], ...] = (
            (),
        )
        self._frame_rects: Tuple[Tuple[pygame.Rect, ...], ...] = ((),)

    @property
    def cached_surface_count(self) -> int:
        return len(self._surface_cache)

    @property
    def frame_rects(self) -> Tuple[Tuple[pygame.Rect, ...], ...]:
        return self._frame_rects

    def update_layout(
        self,
        photo_content_rect: Optional[Tuple[int, int, int, int]],
        card_rect: pygame.Rect,
        text_rects: Iterable[pygame.Rect],
    ) -> None:
        """Reposition decorations without discarding any cached shape surfaces."""

        if not self.show:
            self.placements = ()
            self._render_frames = ((),)
            self._frame_rects = ((),)
            return

        protected_rects = tuple(text_rects)
        self.placements = self._place_decorations(
            photo_content_rect,
            card_rect,
            protected_rects,
        )
        self._prepare_render_frames(protected_rects)

    def frame_index(self, now: float) -> int:
        if not self.animate or len(self._render_frames) == 1:
            return 0
        return int(max(0.0, now) / PULSE_FRAME_SECONDS) % len(self._render_frames)

    def render(self, target: pygame.Surface, now: float) -> None:
        """Blit one pre-rendered deterministic frame without allocating surfaces."""

        if not self.show or not self._render_frames:
            return
        for surface, position in self._render_frames[self.frame_index(now)]:
            target.blit(surface, position)

    def _place_decorations(
        self,
        photo_content_rect: Optional[Tuple[int, int, int, int]],
        card_rect: pygame.Rect,
        protected_rects: Tuple[pygame.Rect, ...],
    ) -> Tuple[DecorationPlacement, ...]:
        width, height = self.display_size
        screen = pygame.Rect(0, 0, width, height)
        display_scale = min(width / 1024, height / 600)
        margin = max(6, round(18 * display_scale))
        content = pygame.Rect(photo_content_rect) if photo_content_rect else None
        if self.density == "low":
            return self._place_sparse_decorations(
                screen,
                content,
                card_rect,
                protected_rects,
                display_scale,
                margin,
            )

        letterbox_layout = self._letterbox_layout(screen, content)
        if letterbox_layout is None:
            return self._place_sparse_decorations(
                screen,
                content,
                card_rect,
                protected_rects,
                display_scale,
                margin,
            )

        orientation, bars = letterbox_layout
        templates = self._templates_for(orientation)
        card_exclusion = card_rect.inflate(margin * 2, margin * 2)
        placements: List[DecorationPlacement] = []
        for bar, template in zip(bars, templates):
            area_ratio = min(
                1.0,
                bar.width * bar.height
                / (screen.width * screen.height * REFERENCE_BAR_AREA_RATIO),
            )
            motif_budget = round(len(template) * area_ratio)
            for anchor in template[:motif_budget]:
                placement = self._placement_from_anchor(
                    bar,
                    anchor,
                    display_scale,
                )
                if self._placement_is_safe(
                    placement,
                    screen,
                    protected_rects,
                    placements,
                    avoid_rects=(content, card_exclusion),
                ):
                    placements.append(placement)
        if self.density == "high":
            extra_limit = round(len(placements) * 0.3)
            extra_templates = self._high_templates_for(orientation)
            for anchor_index in range(max(map(len, extra_templates))):
                for bar, template in zip(bars, extra_templates):
                    if extra_limit <= 0:
                        return tuple(placements)
                    if anchor_index >= len(template):
                        continue
                    placement = self._placement_from_anchor(
                        bar,
                        template[anchor_index],
                        display_scale,
                    )
                    if self._placement_is_safe(
                        placement,
                        screen,
                        protected_rects,
                        placements,
                        avoid_rects=(content, card_exclusion),
                    ):
                        placements.append(placement)
                        extra_limit -= 1
        return tuple(placements)

    def _place_sparse_decorations(
        self,
        screen: pygame.Rect,
        content: Optional[pygame.Rect],
        card_rect: pygame.Rect,
        protected_rects: Tuple[pygame.Rect, ...],
        display_scale: float,
        margin: int,
    ) -> Tuple[DecorationPlacement, ...]:
        placements: List[DecorationPlacement] = []
        medium_scale = max(1, round(4 * display_scale))
        small_scale = max(1, round(2 * display_scale))

        for corner in ("upper_left", "lower_right"):
            placement = self._main_heart_placement(
                corner,
                screen,
                content,
                medium_scale,
                margin,
            )
            placement = self._move_outside_card(placement, card_rect, screen, margin)
            if self._placement_is_safe(placement, screen, protected_rects, placements):
                placements.append(placement)

        candidates = self._accent_candidates(card_rect, small_scale, margin)
        accent_width, accent_height = self._shape_size("small_heart", small_scale + 1, 0)
        has_usable_letterbox = content is not None and (
            content.left >= accent_width
            or screen.right - content.right >= accent_width
            or content.top >= accent_height
            or screen.bottom - content.bottom >= accent_height
        )
        accent_avoid_rects = (card_rect, content) if has_usable_letterbox else (card_rect,)
        for index, center in enumerate(candidates):
            if len(placements) >= 4:
                break
            kind = "small_heart" if index % 2 == 0 else "sparkle"
            placement = DecorationPlacement(kind, center, small_scale)
            if not self._placement_is_safe(
                placement,
                screen,
                protected_rects,
                placements,
                avoid_rects=accent_avoid_rects,
            ):
                continue
            placements.append(placement)
        return tuple(placements)

    def _letterbox_layout(
        self,
        screen: pygame.Rect,
        content: Optional[pygame.Rect],
    ) -> Optional[Tuple[str, Tuple[pygame.Rect, pygame.Rect]]]:
        if content is None:
            return None

        left_width = max(0, content.left - screen.left)
        right_width = max(0, screen.right - content.right)
        top_height = max(0, content.top - screen.top)
        bottom_height = max(0, screen.bottom - content.bottom)
        if left_width or right_width:
            return (
                "vertical",
                (
                    pygame.Rect(screen.left, screen.top, left_width, screen.height),
                    pygame.Rect(content.right, screen.top, right_width, screen.height),
                ),
            )
        if top_height or bottom_height:
            return (
                "horizontal",
                (
                    pygame.Rect(screen.left, screen.top, screen.width, top_height),
                    pygame.Rect(screen.left, content.bottom, screen.width, bottom_height),
                ),
            )
        return None

    def _templates_for(
        self,
        orientation: str,
    ) -> Tuple[Tuple[MotifAnchor, ...], Tuple[MotifAnchor, ...]]:
        if orientation == "vertical":
            return VERTICAL_LEFT_TEMPLATE, VERTICAL_RIGHT_TEMPLATE
        return HORIZONTAL_TOP_TEMPLATE, HORIZONTAL_BOTTOM_TEMPLATE

    @staticmethod
    def _high_templates_for(
        orientation: str,
    ) -> Tuple[Tuple[MotifAnchor, ...], Tuple[MotifAnchor, ...]]:
        if orientation == "vertical":
            return VERTICAL_LEFT_HIGH, VERTICAL_RIGHT_HIGH
        return HORIZONTAL_TOP_HIGH, HORIZONTAL_BOTTOM_HIGH

    @staticmethod
    def _placement_from_anchor(
        bar: pygame.Rect,
        anchor: MotifAnchor,
        display_scale: float,
    ) -> DecorationPlacement:
        base_scale = {"small": 2, "medium": 4, "large": 5}[anchor.size]
        scale = max(1, round(base_scale * display_scale))
        center = (
            bar.left + round(anchor.x * bar.width),
            bar.top + round(anchor.y * bar.height),
        )
        return DecorationPlacement(anchor.kind, center, scale)

    def _move_outside_card(
        self,
        placement: DecorationPlacement,
        card_rect: pygame.Rect,
        screen: pygame.Rect,
        margin: int,
    ) -> DecorationPlacement:
        rectangle = self._placement_rect(placement, 1)
        if not rectangle.colliderect(card_rect):
            return placement

        right_center_x = card_rect.right + margin + rectangle.width // 2
        if right_center_x + rectangle.width // 2 <= screen.right:
            return DecorationPlacement(
                placement.kind,
                (right_center_x, placement.center[1]),
                placement.scale,
            )

        above_center_y = card_rect.top - margin - rectangle.height // 2
        return DecorationPlacement(
            placement.kind,
            (placement.center[0], above_center_y),
            placement.scale,
        )

    def _main_heart_placement(
        self,
        corner: str,
        screen: pygame.Rect,
        content: Optional[pygame.Rect],
        scale: int,
        margin: int,
    ) -> DecorationPlacement:
        largest_scale = scale + (1 if scale >= 2 else 0)
        shape_width, shape_height = self._shape_size("heart", largest_scale, 0)
        half_width = shape_width // 2
        half_height = shape_height // 2
        fallback_scale = max(1, scale - 1)

        if content is not None:
            if corner == "upper_left" and content.left >= shape_width + 2 * margin:
                return DecorationPlacement(
                    "heart",
                    (content.left // 2, margin + half_height),
                    scale,
                )
            if corner == "lower_right" and screen.right - content.right >= shape_width + 2 * margin:
                return DecorationPlacement(
                    "heart",
                    ((content.right + screen.right) // 2, screen.bottom - margin - half_height),
                    scale,
                )
            if corner == "upper_left" and content.top >= shape_height + 2 * margin:
                return DecorationPlacement(
                    "heart",
                    (margin + half_width, content.top // 2),
                    scale,
                )
            lower_bar_height = screen.bottom - content.bottom
            if corner == "lower_right" and lower_bar_height >= shape_height + 2 * margin:
                return DecorationPlacement(
                    "heart",
                    (screen.right - margin - half_width, (content.bottom + screen.bottom) // 2),
                    scale,
                )

        fallback_width, fallback_height = self._shape_size("heart", fallback_scale, 1)
        if corner == "upper_left":
            center = (margin + fallback_width // 2, margin + fallback_height // 2)
        else:
            center = (
                screen.right - margin - fallback_width // 2,
                screen.bottom - margin - fallback_height // 2,
            )
        return DecorationPlacement("heart", center, fallback_scale)

    def _accent_candidates(
        self,
        card_rect: pygame.Rect,
        scale: int,
        margin: int,
    ) -> Tuple[Point, ...]:
        shape_width, shape_height = self._shape_size("small_heart", scale, 0)
        horizontal_gap = margin + shape_width // 2
        vertical_gap = margin + shape_height // 2
        return (
            (card_rect.left - horizontal_gap, card_rect.top + card_rect.height // 3),
            (card_rect.right + horizontal_gap, card_rect.top + card_rect.height // 3),
            (card_rect.left + card_rect.width // 4, card_rect.top - vertical_gap),
            (card_rect.right - card_rect.width // 4, card_rect.top - vertical_gap),
            (card_rect.left - horizontal_gap, card_rect.top + 2 * card_rect.height // 3),
            (card_rect.right + horizontal_gap, card_rect.top + 2 * card_rect.height // 3),
            (card_rect.centerx, card_rect.top - vertical_gap),
            (card_rect.centerx, card_rect.bottom + vertical_gap),
        )

    def _placement_is_safe(
        self,
        placement: DecorationPlacement,
        screen: pygame.Rect,
        protected_rects: Tuple[pygame.Rect, ...],
        existing: Sequence[DecorationPlacement],
        avoid_rects: Sequence[Optional[pygame.Rect]] = (),
    ) -> bool:
        rectangle = self._placement_rect(placement, 1)
        if not screen.contains(rectangle):
            return False
        if any(
            avoid_rect is not None and rectangle.colliderect(avoid_rect)
            for avoid_rect in avoid_rects
        ):
            return False
        if any(rectangle.colliderect(protected) for protected in protected_rects):
            return False
        return not any(
            rectangle.colliderect(self._placement_rect(other, 1)) for other in existing
        )

    def _prepare_render_frames(
        self,
        protected_rects: Tuple[pygame.Rect, ...],
    ) -> None:
        frame_count = PULSE_FRAME_COUNT if self.animate else 1
        render_frames = []
        frame_rects = []
        for frame_index in range(frame_count):
            rendered = []
            rectangles = []
            for placement in self.placements:
                surface = self._surface_for(placement, frame_index)
                rectangle = surface.get_rect(center=placement.center)
                if any(rectangle.colliderect(protected) for protected in protected_rects):
                    continue
                rendered.append((surface, rectangle.topleft))
                rectangles.append(rectangle)
            render_frames.append(tuple(rendered))
            frame_rects.append(tuple(rectangles))
        self._render_frames = tuple(render_frames)
        self._frame_rects = tuple(frame_rects)

    def _surface_for(
        self,
        placement: DecorationPlacement,
        frame_index: int,
    ) -> pygame.Surface:
        pulse_delta = self._pulse_delta(placement, frame_index)
        scale = placement.scale + pulse_delta
        primary_color, secondary_color = self._colors_for_kind(placement.kind)
        cache_key = (
            placement.kind,
            scale,
            frame_index if pulse_delta else 0,
            primary_color,
            secondary_color,
        )
        cached = self._surface_cache.get(cache_key)
        if cached is not None:
            return cached

        width, height = self._shape_size(placement.kind, scale, 0)
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        if placement.kind in {"heart", "large_heart"}:
            draw_pixel_heart(
                surface,
                (0, 0),
                scale,
                self.heart_color,
                self.highlight_color,
            )
        elif placement.kind == "small_heart":
            draw_small_pixel_heart(
                surface,
                (0, 0),
                scale,
                self.heart_color,
                self.highlight_color,
            )
        elif placement.kind == "outline_heart":
            draw_outlined_pixel_heart(
                surface,
                (0, 0),
                scale,
                self.heart_color,
                self.highlight_color,
            )
        elif placement.kind == "diamond":
            draw_tiny_pixel_diamond(surface, (0, 0), scale, self.sparkle_color)
        elif placement.kind == "trail":
            draw_dotted_pixel_trail(surface, (0, 0), scale, self.soft_accent_color)
        else:
            draw_four_point_sparkle(surface, (0, 0), scale, self.sparkle_color)
        self._surface_cache[cache_key] = surface
        return surface

    def _placement_rect(
        self,
        placement: DecorationPlacement,
        frame_index: int,
    ) -> pygame.Rect:
        width, height = self._shape_size(
            placement.kind,
            placement.scale + self._pulse_delta(placement, frame_index),
            0,
        )
        return pygame.Rect(0, 0, width, height).move(
            placement.center[0] - width // 2,
            placement.center[1] - height // 2,
        )

    @staticmethod
    def _shape_size(kind: str, scale: int, frame_index: int) -> Tuple[int, int]:
        del frame_index
        pattern = PixelDecorationRenderer._pattern_for_kind(kind)
        return len(pattern[0]) * scale, len(pattern) * scale

    def _colors_for_kind(self, kind: str) -> Tuple[Color, Color]:
        if kind in {"heart", "large_heart", "small_heart", "outline_heart"}:
            return self.heart_color, self.highlight_color
        if kind == "trail":
            return self.soft_accent_color, self.soft_accent_color
        return self.sparkle_color, self.sparkle_color

    @staticmethod
    def _pattern_for_kind(kind: str) -> Sequence[str]:
        return {
            "heart": MEDIUM_HEART_PATTERN,
            "large_heart": MEDIUM_HEART_PATTERN,
            "small_heart": SMALL_HEART_PATTERN,
            "outline_heart": OUTLINED_HEART_PATTERN,
            "sparkle": SPARKLE_PATTERN,
            "diamond": DIAMOND_PATTERN,
            "trail": DOTTED_TRAIL_PATTERN,
        }[kind]

    @staticmethod
    def _pulse_delta(placement: DecorationPlacement, frame_index: int) -> int:
        is_heart = placement.kind in {"heart", "large_heart"}
        return 1 if is_heart and frame_index == 1 and placement.scale >= 2 else 0
