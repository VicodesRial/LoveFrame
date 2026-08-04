import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest
from PIL import Image

import app.ui as ui_module
from app.config import AppConfig
from app.photo_loader import (
    NavigationDirection,
    PhotoPrefetchWorker,
    PreparedPhoto,
)
from app.ui import (
    LoveFrameUI,
    MINIMUM_MESSAGE_FONT_SIZE,
    TouchAction,
    build_message_overlay,
    create_message_card_layout,
    cursor_should_hide,
    fade_progress,
    format_clock_time,
    image_to_surface,
    is_recent_activation,
    scaled_font_size,
    touch_action_for_position,
    wrap_message,
)


@pytest.fixture(autouse=True)
def close_pygame_after_test():
    yield
    pygame.quit()


@pytest.mark.parametrize(
    ("x_position", "expected"),
    [
        (0, TouchAction.PREVIOUS),
        (32, TouchAction.PREVIOUS),
        (34, TouchAction.TOGGLE_MESSAGE),
        (65, TouchAction.TOGGLE_MESSAGE),
        (67, TouchAction.NEXT),
        (99, TouchAction.NEXT),
    ],
)
def test_touch_zones(x_position: int, expected: TouchAction) -> None:
    assert touch_action_for_position(x_position, 100) is expected


def test_center_action_toggles_message(tmp_path: Path) -> None:
    interface = LoveFrameUI(AppConfig(photo_path=tmp_path))

    interface._activate(TouchAction.TOGGLE_MESSAGE, 0)

    assert interface.message_visible is False
    interface.photo_loader.close()


def test_fade_progress_is_clamped() -> None:
    assert fade_progress(99.0, 100.0, 0.4) == 0.0
    assert fade_progress(100.2, 100.0, 0.4) == pytest.approx(0.5)
    assert fade_progress(100.7, 100.0, 0.4) == 1.0
    assert fade_progress(100.0, 100.0, 0.0) == 1.0


def test_cursor_hides_at_timeout_boundary() -> None:
    assert cursor_should_hide(3.999, 1.0, 3.0) is False
    assert cursor_should_hide(4.0, 1.0, 3.0) is True


def test_elapsed_helpers_cross_old_pygame_tick_boundary() -> None:
    old_tick_boundary = (2**32) / 1_000
    started_at = old_tick_boundary - 0.2

    assert fade_progress(old_tick_boundary + 0.2, started_at, 0.4) == 1.0
    assert cursor_should_hide(old_tick_boundary + 3.0, started_at, 3.0) is True
    assert is_recent_activation(old_tick_boundary + 0.04, old_tick_boundary - 0.04)


def test_message_wrap_and_overlay_fit_display() -> None:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((320, 180))
    clock_font = pygame.font.SysFont("DejaVu Sans", 10, bold=True)
    message_font = pygame.font.SysFont("DejaVu Sans", 8)
    message = "A lovely message that needs more than one line on this small display."

    lines = wrap_message(message, message_font, 180)
    overlay = build_message_overlay(
        (320, 180),
        message,
        "8:14 AM",
        True,
        clock_font,
        8,
        8,
    )

    assert len(lines) > 1
    assert all(message_font.size(line)[0] <= 180 for line in lines)
    assert overlay.get_size() == (320, 180)


def _surface_contains_color(surface: pygame.Surface, color) -> bool:
    return any(
        surface.get_at((x, y))[:3] == color
        for x in range(surface.get_width())
        for y in range(surface.get_height())
    )


def test_message_card_uses_configured_pink_theme_colors_and_opacity() -> None:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((320, 180))
    clock_font = pygame.font.SysFont("DejaVu Sans", 12, bold=True)
    card_color = (210, 140, 160)
    text_color = (45, 20, 32)
    clock_color = (60, 25, 40)
    opacity = 177
    layout = create_message_card_layout(
        (320, 180),
        "A generated message.",
        "8:14 AM",
        True,
        clock_font,
        10,
        8,
        text_color,
        clock_color,
    )
    overlay = build_message_overlay(
        (320, 180),
        "A generated message.",
        "8:14 AM",
        True,
        clock_font,
        10,
        8,
        card_color,
        opacity,
        text_color,
        clock_color,
    )

    card_sample = (layout.card_rect.left + 5, layout.card_rect.centery)
    assert overlay.get_at(card_sample) == (*card_color, opacity)
    assert _surface_contains_color(layout.clock_surface, clock_color)
    assert all(
        _surface_contains_color(surface, text_color)
        for surface in layout.message_surfaces
    )


def test_interface_applies_configured_theme_to_cached_overlay(
    tmp_path: Path, monkeypatch
) -> None:
    pygame.font.init()
    config = AppConfig(
        photo_path=tmp_path,
        card_background_color="#D28CA0",
        card_opacity=177,
        text_color="#2D1420",
        clock_color="#3C1928",
    )
    interface = LoveFrameUI(config)
    interface._initialize_fonts()
    captured = []

    def recording_builder(*args):
        captured.append(args)
        return pygame.Surface((config.width, config.height), pygame.SRCALPHA)

    monkeypatch.setattr(ui_module, "build_message_overlay", recording_builder)

    interface._rebuild_message_overlay()

    assert captured[0][7:11] == (
        (210, 140, 160),
        177,
        (45, 20, 32),
        (60, 25, 40),
    )
    interface.photo_loader.close()


def test_decorations_do_not_change_navigation_hitboxes(tmp_path: Path) -> None:
    pygame.font.init()
    before = [touch_action_for_position(x_position, 300) for x_position in (20, 150, 280)]
    interface = LoveFrameUI(AppConfig(width=300, height=180, photo_path=tmp_path))

    interface._initialize_fonts()
    interface._rebuild_message_overlay()

    after = [touch_action_for_position(x_position, 300) for x_position in (20, 150, 280)]
    assert after == before == [
        TouchAction.PREVIOUS,
        TouchAction.TOGGLE_MESSAGE,
        TouchAction.NEXT,
    ]
    interface.photo_loader.close()


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(0, "12:14 AM"), (8, "8:14 AM"), (12, "12:14 PM"), (20, "8:14 PM")],
)
def test_12_hour_clock_format(hour: int, expected: str) -> None:
    value = datetime(2026, 8, 3, hour, 14, tzinfo=ZoneInfo("America/New_York"))

    assert format_clock_time(value, "12h") == expected


def test_24_hour_clock_format() -> None:
    morning = datetime(2026, 8, 3, 8, 14, tzinfo=ZoneInfo("America/New_York"))
    evening = datetime(2026, 8, 3, 20, 14, tzinfo=ZoneInfo("America/New_York"))

    assert format_clock_time(morning, "24h") == "08:14"
    assert format_clock_time(evening, "24h") == "20:14"


def test_invalid_clock_format_falls_back_to_12_hour() -> None:
    value = datetime(2026, 8, 3, 8, 14, tzinfo=ZoneInfo("America/New_York"))

    assert format_clock_time(value, "seconds") == "8:14 AM"


def test_clock_uses_configured_timezone() -> None:
    instant = datetime(2026, 7, 1, 13, 14, tzinfo=timezone.utc)

    assert format_clock_time(instant, timezone_name="America/New_York") == "9:14 AM"
    assert format_clock_time(instant, timezone_name="UTC") == "1:14 PM"


def test_default_message_provider_keeps_8am_new_york_rollover(tmp_path: Path) -> None:
    message_path = tmp_path / "messages.json"
    message_path.write_text(
        json.dumps(
            {
                "dated": {
                    "2026-08-02": "Previous-day example.",
                    "2026-08-03": "Current-day example.",
                }
            }
        ),
        encoding="utf-8",
    )
    interface = LoveFrameUI(AppConfig(message_path=message_path, photo_path=tmp_path))

    before_rollover = datetime(2026, 8, 3, 11, 59, tzinfo=timezone.utc)
    at_rollover = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    assert interface._default_message_provider(before_rollover) == "Previous-day example."
    assert interface._default_message_provider(at_rollover) == "Current-day example."
    interface.photo_loader.close()


@pytest.mark.parametrize("display_size", [(1024, 600), (320, 180)])
def test_long_unicode_message_stays_inside_card(display_size) -> None:
    pygame.font.init()
    clock_size = scaled_font_size(34, display_size)
    preferred_size = scaled_font_size(25, display_size)
    minimum_size = min(
        preferred_size,
        scaled_font_size(MINIMUM_MESSAGE_FONT_SIZE, display_size),
    )
    clock_font = pygame.font.SysFont("DejaVu Sans", clock_size, bold=True)
    message_part = (
        "Cœur ❤️ mañana — thank you for making every ordinary moment feel special. "
        "This generated message is intentionally long enough to require several wrapped "
        "lines while preserving every supported Unicode character comfortably."
    )
    message = " ".join([message_part] * 8)

    layout = create_message_card_layout(
        display_size,
        message,
        "8:14 AM",
        True,
        clock_font,
        preferred_size,
        minimum_size,
    )
    screen_rect = pygame.Rect((0, 0), display_size)

    assert screen_rect.contains(layout.card_rect)
    assert all(layout.card_rect.contains(rect) for rect in layout.content_rects)
    assert minimum_size <= layout.message_font_size <= preferred_size
    if display_size == (1024, 600):
        assert layout.message_font_size < preferred_size
    assert all(abs(rect.centerx - screen_rect.centerx) <= 1 for rect in layout.content_rects)
    preferred_font = pygame.font.SysFont("DejaVu Sans", preferred_size)
    assert "Cœur" in " ".join(wrap_message(message, preferred_font, display_size[0]))


class FakePhotoLoader:
    def __init__(self) -> None:
        self.first = PreparedPhoto(Image.new("RGB", (100, 60), "red"), Path("first.jpg"))
        self.second = PreparedPhoto(Image.new("RGB", (100, 60), "blue"), Path("second.jpg"))
        self.advance_calls = 0
        self.previous_calls = 0

    def current(self) -> PreparedPhoto:
        return self.first

    def advance(self) -> PreparedPhoto:
        self.advance_calls += 1
        return self.second

    def previous(self) -> PreparedPhoto:
        self.previous_calls += 1
        return self.first

    def close(self) -> None:
        self.first.image.close()
        self.second.image.close()


class BlockingPhotoLoader(FakePhotoLoader):
    def __init__(self) -> None:
        super().__init__()
        self.prepare_started = threading.Event()
        self.release_prepare = threading.Event()

    def prepare_next(self) -> PreparedPhoto:
        self.prepare_started.set()
        self.release_prepare.wait()
        return self.second


class FakePrefetchWorker:
    def __init__(self) -> None:
        self.requests = []
        self.ready = None
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def request(self, direction: NavigationDirection) -> bool:
        if self.requests:
            return False
        self.requests.append(direction)
        return True

    def take_ready(self):
        ready = self.ready
        self.ready = None
        return ready

    def shutdown(self) -> None:
        self.stopped = True


class FakeClock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class MutableWallClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def test_touch_generated_mouse_event_is_not_handled_twice() -> None:
    pygame.display.init()
    pygame.display.set_mode((100, 60))
    loader = FakePhotoLoader()
    prefetch_worker = FakePrefetchWorker()
    interface = LoveFrameUI(
        AppConfig(width=100, height=60, fade_duration_ms=0),
        photo_loader=loader,
        prefetch_worker=prefetch_worker,
    )
    interface._current_surface = image_to_surface(loader.current().image)
    interface._current_path = loader.current().path
    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (90, 30), "touch": True},
        )
    )
    pygame.event.post(pygame.event.Event(pygame.FINGERUP, {"x": 0.9, "y": 0.5}))

    assert interface._handle_events(1_000) is True
    assert prefetch_worker.requests == [NavigationDirection.NEXT]
    loader.close()


def test_event_processing_returns_while_background_decode_is_blocked() -> None:
    pygame.display.init()
    pygame.display.set_mode((100, 60))
    loader = BlockingPhotoLoader()
    worker = PhotoPrefetchWorker(loader)
    worker.start()
    assert loader.prepare_started.wait(timeout=2.0)
    interface = LoveFrameUI(
        AppConfig(width=100, height=60),
        photo_loader=loader,
        prefetch_worker=worker,
    )
    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (90, 30), "touch": False},
        )
    )

    assert interface._handle_events(100.0) is True
    assert interface._pending_navigation is TouchAction.NEXT
    assert loader.advance_calls == 0
    assert loader.release_prepare.is_set() is False

    loader.release_prepare.set()
    worker.shutdown()
    assert worker.is_alive is False
    loader.close()


def test_monotonic_deduplication_crosses_old_tick_boundary(tmp_path: Path) -> None:
    pygame.display.init()
    pygame.display.set_mode((100, 60))
    old_tick_boundary = (2**32) / 1_000
    loader = FakePhotoLoader()
    interface = LoveFrameUI(
        AppConfig(width=100, height=60, photo_path=tmp_path),
        photo_loader=loader,
        prefetch_worker=FakePrefetchWorker(),
    )

    pygame.event.post(pygame.event.Event(pygame.FINGERUP, {"x": 0.5, "y": 0.5}))
    interface._handle_events(old_tick_boundary - 0.05)
    assert interface.message_visible is False

    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (50, 30), "touch": False},
        )
    )
    interface._handle_events(old_tick_boundary + 0.05)
    assert interface.message_visible is False

    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (50, 30), "touch": False},
        )
    )
    interface._handle_events(old_tick_boundary + 0.30)
    assert interface.message_visible is True
    loader.close()


def test_rotation_and_message_poll_use_injected_monotonic_clock(tmp_path: Path) -> None:
    old_tick_boundary = (2**32) / 1_000
    clock = FakeClock(old_tick_boundary - 1.0)
    loader = FakePhotoLoader()
    prefetch_worker = FakePrefetchWorker()
    provider_calls = []
    interface = LoveFrameUI(
        AppConfig(
            photo_path=tmp_path,
            slideshow_interval_seconds=10,
            message_poll_seconds=60,
        ),
        message_provider=lambda: provider_calls.append(clock()) or "Example",
        photo_loader=loader,
        prefetch_worker=prefetch_worker,
        clock=clock,
    )
    interface._photo_started_at = clock()
    interface._message_polled_at = clock()
    interface._last_pointer_activity_at = clock()
    interface._cursor_visible = False

    clock.advance(10.0)
    interface._update(clock())
    assert prefetch_worker.requests == [NavigationDirection.NEXT]
    assert provider_calls == []

    clock.advance(50.0)
    interface._update(clock())
    assert provider_calls == [clock()]
    loader.close()


def test_clock_overlay_rerenders_only_when_minute_changes(monkeypatch) -> None:
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((320, 180))
    wall_clock = MutableWallClock(datetime(2026, 8, 3, 12, 14, 5, tzinfo=timezone.utc))
    loader = FakePhotoLoader()
    interface = LoveFrameUI(
        AppConfig(width=320, height=180, timezone_name="UTC"),
        message_provider=lambda: "A stable generated message.",
        photo_loader=loader,
        prefetch_worker=FakePrefetchWorker(),
        now_provider=wall_clock,
    )
    interface._initialize_fonts()
    interface._photo_started_at = 100.0
    interface._last_pointer_activity_at = 100.0
    interface._cursor_visible = False
    overlay_builds = []
    original_builder = ui_module.build_message_overlay

    def recording_builder(*args, **kwargs):
        overlay_builds.append(True)
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(ui_module, "build_message_overlay", recording_builder)

    interface._update(100.0)
    first_overlay = interface._message_overlay
    wall_clock.now = datetime(2026, 8, 3, 12, 14, 45, tzinfo=timezone.utc)
    interface._update(101.0)

    assert interface._message_overlay is first_overlay
    assert overlay_builds == [True]

    wall_clock.now = datetime(2026, 8, 3, 12, 15, tzinfo=timezone.utc)
    interface._update(102.0)

    assert interface._message_overlay is not first_overlay
    assert interface._clock_text == "12:15 PM"
    assert overlay_builds == [True, True]
    loader.close()


def test_center_action_hides_and_restores_clock_and_message_card() -> None:
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((320, 180))
    clock_font = pygame.font.SysFont("DejaVu Sans", 10, bold=True)
    overlay = build_message_overlay(
        (320, 180),
        "A generated message.",
        "8:14 AM",
        True,
        clock_font,
        8,
        8,
    )
    layout = create_message_card_layout(
        (320, 180),
        "A generated message.",
        "8:14 AM",
        True,
        clock_font,
        8,
        8,
    )
    loader = FakePhotoLoader()
    interface = LoveFrameUI(
        AppConfig(width=320, height=180),
        photo_loader=loader,
        prefetch_worker=FakePrefetchWorker(),
    )
    interface._screen = screen
    interface._current_surface = pygame.Surface((320, 180))
    interface._current_surface.fill((200, 40, 40))
    interface._message_overlay = overlay
    decoration_render_calls = []

    class RecordingDecorations:
        def render(self, target, now):
            decoration_render_calls.append(now)

    interface._decorations = RecordingDecorations()
    sample_position = layout.card_rect.center

    interface._activate(TouchAction.TOGGLE_MESSAGE, 0.0)
    interface._render(0.0)
    hidden_pixel = screen.get_at(sample_position)

    interface._activate(TouchAction.TOGGLE_MESSAGE, 0.0)
    interface._render(0.0)
    visible_pixel = screen.get_at(sample_position)

    assert hidden_pixel[:3] == (200, 40, 40)
    assert visible_pixel[:3] != hidden_pixel[:3]
    assert decoration_render_calls == [0.0, 0.0]
    loader.close()


def test_ready_photo_is_converted_and_promoted_on_main_thread() -> None:
    pygame.display.init()
    pygame.display.set_mode((100, 60))
    loader = FakePhotoLoader()
    prefetch_worker = FakePrefetchWorker()
    prefetch_worker.ready = loader.second
    interface = LoveFrameUI(
        AppConfig(width=100, height=60, fade_duration_ms=0),
        photo_loader=loader,
        prefetch_worker=prefetch_worker,
    )
    interface._current_surface = image_to_surface(loader.first.image)
    interface._current_path = loader.first.path
    interface._pending_navigation = TouchAction.NEXT

    interface._consume_ready_photo(50.0)

    assert interface._current_path == loader.second.path
    assert interface._current_surface.get_size() == (100, 60)
    assert interface._pending_navigation is None
    assert interface._photo_started_at == 50.0
    loader.close()


def test_headless_ui_smoke_uses_generated_content(tmp_path: Path) -> None:
    photo_path = tmp_path / "photos"
    photo_path.mkdir()
    image = Image.new("RGB", (640, 480), (40, 80, 120))
    image.save(photo_path / "generated.jpg")
    image.close()
    provider_calls = []

    def message_provider() -> str:
        provider_calls.append(True)
        return "A generated test message."

    interface = LoveFrameUI(
        AppConfig(
            width=320,
            height=180,
            photo_path=photo_path,
            fullscreen=False,
            fade_duration_ms=100,
            frames_per_second=30,
        ),
        message_provider=message_provider,
    )

    assert interface.run(max_frames=3) == 0
    assert provider_calls == [True]
