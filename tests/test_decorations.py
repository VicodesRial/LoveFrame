import os
from itertools import combinations

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from app.config import AppConfig
from app.decorations import (
    PixelDecorationRenderer,
    draw_dotted_pixel_trail,
    draw_four_point_sparkle,
    draw_outlined_pixel_heart,
    draw_pixel_heart,
    draw_small_pixel_heart,
    draw_tiny_pixel_diamond,
)


@pytest.fixture(autouse=True)
def close_pygame_after_test():
    yield
    pygame.quit()


@pytest.mark.parametrize("scale", [1, 2, 4])
def test_pixel_heart_geometry_uses_integer_grid(scale: int) -> None:
    surface = pygame.Surface((80, 60), pygame.SRCALPHA)
    origin = (3, 5)

    rectangles = draw_pixel_heart(
        surface,
        origin,
        scale,
        (216, 91, 123),
        (255, 240, 244),
    )

    assert rectangles
    assert all(rectangle.size == (scale, scale) for rectangle in rectangles)
    assert all((rectangle.x - origin[0]) % scale == 0 for rectangle in rectangles)
    assert all((rectangle.y - origin[1]) % scale == 0 for rectangle in rectangles)
    assert max(rectangle.right for rectangle in rectangles) <= origin[0] + 8 * scale
    assert max(rectangle.bottom for rectangle in rectangles) <= origin[1] + 6 * scale


def test_small_heart_and_sparkle_use_custom_exact_colors() -> None:
    surface = pygame.Surface((40, 20), pygame.SRCALPHA)
    heart_color = (1, 2, 3)
    highlight_color = (4, 5, 6)
    sparkle_color = (7, 8, 9)

    draw_small_pixel_heart(
        surface,
        (0, 0),
        2,
        heart_color,
        highlight_color,
    )
    draw_four_point_sparkle(surface, (20, 0), 2, sparkle_color)

    colors = {
        surface.get_at((x, y))[:3]
        for x in range(surface.get_width())
        for y in range(surface.get_height())
        if surface.get_at((x, y)).a
    }
    assert colors == {heart_color, highlight_color, sparkle_color}


def test_outline_diamond_and_dotted_trail_use_integer_pixels() -> None:
    surface = pygame.Surface((80, 40), pygame.SRCALPHA)

    outline = draw_outlined_pixel_heart(surface, (0, 0), 2, (1, 2, 3), (4, 5, 6))
    diamond = draw_tiny_pixel_diamond(surface, (30, 0), 2, (7, 8, 9))
    trail = draw_dotted_pixel_trail(surface, (45, 0), 2, (10, 11, 12))

    assert all(rectangle.size == (2, 2) for rectangle in outline + diamond + trail)
    assert len(trail) == 3


def test_renderer_uses_default_decoration_palette() -> None:
    renderer = PixelDecorationRenderer((1024, 600), AppConfig())
    renderer.update_layout(
        (392, 0, 240, 600),
        pygame.Rect(180, 420, 664, 140),
        (),
    )
    rendered_colors = set()
    for surface, _position in renderer._render_frames[0]:
        rendered_colors.update(
            surface.get_at((x, y))[:3]
            for x in range(surface.get_width())
            for y in range(surface.get_height())
            if surface.get_at((x, y)).a
        )

    assert (216, 91, 123) in rendered_colors
    assert (255, 240, 244) in rendered_colors
    assert (201, 79, 112) in rendered_colors


def _renderer_for(
    density: str,
    content_rect=(392, 0, 240, 600),
) -> PixelDecorationRenderer:
    renderer = PixelDecorationRenderer((1024, 600), AppConfig(decoration_density=density))
    renderer.update_layout(
        content_rect,
        pygame.Rect(180, 420, 664, 140),
        (pygame.Rect(360, 450, 304, 70),),
    )
    return renderer


def test_density_levels_have_controlled_relative_counts() -> None:
    low = _renderer_for("low")
    medium = _renderer_for("medium")
    high = _renderer_for("high")

    assert len(low.placements) == 4
    assert 14 <= len(medium.placements) <= 18
    assert len(medium.placements) > len(low.placements)
    assert len(medium.placements) < len(high.placements)
    assert len(high.placements) <= round(len(medium.placements) * 1.3)


def test_motif_count_scales_down_with_actual_sidebar_area() -> None:
    wide = _renderer_for("medium", (392, 0, 240, 600))
    narrow = _renderer_for("medium", (100, 0, 824, 600))
    very_narrow = _renderer_for("medium", (50, 0, 924, 600))

    assert len(wide.placements) > len(narrow.placements) > len(very_narrow.placements)


@pytest.mark.parametrize(
    "content_rect",
    [(392, 0, 240, 600), (100, 0, 824, 600), (50, 0, 924, 600)],
)
def test_high_density_increase_stays_controlled_for_each_bar_area(content_rect) -> None:
    medium = _renderer_for("medium", content_rect)
    high = _renderer_for("high", content_rect)

    assert len(high.placements) >= len(medium.placements)
    assert len(high.placements) <= round(len(medium.placements) * 1.3)


def test_vertical_constellation_is_deterministic_asymmetric_and_safe() -> None:
    content_rect = pygame.Rect(392, 0, 240, 600)
    card_rect = pygame.Rect(180, 420, 664, 140)
    card_exclusion = card_rect.inflate(36, 36)
    first = PixelDecorationRenderer((1024, 600), AppConfig())
    second = PixelDecorationRenderer((1024, 600), AppConfig())
    for renderer in (first, second):
        renderer.update_layout(
            tuple(content_rect),
            card_rect,
            (pygame.Rect(360, 450, 304, 70),),
        )

    assert first.placements == second.placements
    assert first.frame_rects == second.frame_rects
    assert [placement.center for placement in first.placements[:9]] != [
        (1024 - placement.center[0], placement.center[1])
        for placement in first.placements[9:]
    ]

    left_bar = pygame.Rect(0, 0, content_rect.left, 600)
    right_bar = pygame.Rect(content_rect.right, 0, 1024 - content_rect.right, 600)
    screen = pygame.Rect(0, 0, 1024, 600)
    for frame in first.frame_rects:
        assert all(screen.contains(rectangle) for rectangle in frame)
        assert all(
            left_bar.contains(rectangle) or right_bar.contains(rectangle)
            for rectangle in frame
        )
        assert all(not rectangle.colliderect(content_rect) for rectangle in frame)
        assert all(not rectangle.colliderect(card_exclusion) for rectangle in frame)
        assert all(not left.colliderect(right) for left, right in combinations(frame, 2))


def test_horizontal_constellation_stays_in_top_and_bottom_bars() -> None:
    content_rect = pygame.Rect(0, 198, 1024, 204)
    card_rect = pygame.Rect(180, 420, 664, 140)
    renderer = PixelDecorationRenderer((1024, 600), AppConfig())
    renderer.update_layout(
        tuple(content_rect),
        card_rect,
        (pygame.Rect(300, 445, 424, 80),),
    )

    top_bar = pygame.Rect(0, 0, 1024, content_rect.top)
    bottom_bar = pygame.Rect(0, content_rect.bottom, 1024, 600 - content_rect.bottom)
    assert 14 <= len(renderer.placements) <= 18
    for frame in renderer.frame_rects:
        assert all(
            top_bar.contains(rectangle) or bottom_bar.contains(rectangle)
            for rectangle in frame
        )
        assert all(not rectangle.colliderect(content_rect) for rectangle in frame)
        assert all(not left.colliderect(right) for left, right in combinations(frame, 2))


def test_only_medium_and_large_hearts_pulse() -> None:
    renderer = _renderer_for("medium")
    frame_zero = {
        placement.kind: renderer.frame_rects[0][index].size
        for index, placement in enumerate(renderer.placements)
    }
    frame_one = {
        placement.kind: renderer.frame_rects[1][index].size
        for index, placement in enumerate(renderer.placements)
    }

    assert frame_one["heart"] != frame_zero["heart"]
    assert frame_one["large_heart"] != frame_zero["large_heart"]
    for static_kind in ("small_heart", "outline_heart", "sparkle", "diamond", "trail"):
        assert frame_one[static_kind] == frame_zero[static_kind]


def test_decorations_prefer_portrait_letterbox_bars_and_avoid_text() -> None:
    renderer = PixelDecorationRenderer(
        (1024, 600),
        AppConfig(decoration_density="low"),
    )
    renderer.update_layout(
        (392, 0, 240, 600),
        pygame.Rect(180, 420, 664, 140),
        (pygame.Rect(360, 450, 304, 70),),
    )

    largest_frame = renderer.frame_rects[1]
    assert largest_frame[0].right <= 392
    assert largest_frame[1].left >= 632


def test_decorations_prefer_wide_photo_top_and_bottom_bars() -> None:
    renderer = PixelDecorationRenderer(
        (1024, 600),
        AppConfig(decoration_density="low"),
    )
    content_rect = (0, 198, 1024, 204)

    renderer.update_layout(
        content_rect,
        pygame.Rect(180, 420, 664, 140),
        (pygame.Rect(300, 445, 424, 80),),
    )

    largest_frame = renderer.frame_rects[1]
    assert largest_frame[0].bottom <= content_rect[1]
    assert largest_frame[1].top >= content_rect[1] + content_rect[3]


def test_small_display_omits_unsafe_decorations() -> None:
    renderer = PixelDecorationRenderer((320, 180), AppConfig(decoration_density="high"))
    text_rect = pygame.Rect(20, 112, 280, 50)

    renderer.update_layout(
        None,
        pygame.Rect(8, 104, 304, 68),
        (text_rect,),
    )

    screen = pygame.Rect(0, 0, 320, 180)
    assert all(screen.contains(rectangle) for frame in renderer.frame_rects for rectangle in frame)
    assert all(
        not rectangle.colliderect(text_rect)
        for frame in renderer.frame_rects
        for rectangle in frame
    )


def test_show_decorations_false_draws_nothing() -> None:
    renderer = PixelDecorationRenderer((320, 180), AppConfig(show_decorations=False))
    target = pygame.Surface((320, 180))
    target.fill((10, 20, 30))

    renderer.update_layout(None, pygame.Rect(20, 100, 280, 60), ())
    renderer.render(target, 100.0)

    assert renderer.placements == ()
    assert renderer.cached_surface_count == 0
    assert target.get_at((10, 10))[:3] == (10, 20, 30)


def test_pulse_uses_cached_frames_and_injected_monotonic_time() -> None:
    renderer = PixelDecorationRenderer((1024, 600), AppConfig())
    renderer.update_layout(
        (392, 0, 240, 600),
        pygame.Rect(180, 420, 664, 140),
        (pygame.Rect(360, 450, 304, 70),),
    )
    target = pygame.Surface((1024, 600), pygame.SRCALPHA)
    cached_ids = {
        id(surface)
        for frame in renderer._render_frames
        for surface, _position in frame
    }
    cached_count = renderer.cached_surface_count

    assert [renderer.frame_index(value) for value in (0.0, 1.25, 2.5, 3.75)] == [
        0,
        1,
        2,
        0,
    ]
    for value in (0.0, 1.25, 2.5, 3.75, 10_000_000.0):
        renderer.render(target, value)

    assert renderer.cached_surface_count == cached_count
    assert {
        id(surface)
        for frame in renderer._render_frames
        for surface, _position in frame
    } == cached_ids


def test_static_decorations_use_one_cached_render_frame() -> None:
    renderer = PixelDecorationRenderer(
        (1024, 600),
        AppConfig(animate_decorations=False),
    )

    renderer.update_layout(
        (392, 0, 240, 600),
        pygame.Rect(180, 420, 664, 140),
        (),
    )

    assert len(renderer.frame_rects) == 1
    assert renderer.frame_index(100_000.0) == 0
