"""Resource-conscious Pygame interface for LoveFrame."""

from __future__ import annotations

import logging
import time as time_module
from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import Enum
from typing import Callable, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pygame
from PIL import Image

from app.config import AppConfig, hex_color_to_rgb, normalize_clock_format
from app.decorations import PixelDecorationRenderer
from app.message_scheduler import DEFAULT_MESSAGE, get_daily_message
from app.photo_loader import (
    NavigationDirection,
    PhotoLoader,
    PhotoPrefetchWorker,
)

LOGGER = logging.getLogger(__name__)
INPUT_DEDUP_SECONDS = 0.25
REFERENCE_DISPLAY_SIZE = (1024, 600)
MINIMUM_MESSAGE_FONT_SIZE = 16
FONT_NAME = "DejaVu Sans"


class TouchAction(Enum):
    PREVIOUS = "previous"
    TOGGLE_MESSAGE = "toggle_message"
    NEXT = "next"


def touch_action_for_position(x_position: float, width: int) -> TouchAction:
    """Map a horizontal pointer position into one of three equal touch zones."""

    if width <= 0:
        raise ValueError("width must be positive")
    if x_position < width / 3:
        return TouchAction.PREVIOUS
    if x_position < width * 2 / 3:
        return TouchAction.TOGGLE_MESSAGE
    return TouchAction.NEXT


def fade_progress(
    now: float,
    started_at: float,
    duration_seconds: float,
) -> float:
    """Return a clamped 0–1 fade fraction."""

    if duration_seconds <= 0:
        return 1.0
    elapsed = now - started_at
    return max(0.0, min(1.0, elapsed / duration_seconds))


def cursor_should_hide(
    now: float,
    last_activity_at: float,
    timeout_seconds: float,
) -> bool:
    """Return whether cursor inactivity has reached the configured timeout."""

    elapsed = now - last_activity_at
    return timeout_seconds >= 0 and elapsed >= timeout_seconds


def is_recent_activation(
    now: float,
    activated_at: Optional[float],
    window_seconds: float = INPUT_DEDUP_SECONDS,
) -> bool:
    """Return whether an activation occurred inside a monotonic time window."""

    if activated_at is None or window_seconds < 0:
        return False
    elapsed = now - activated_at
    return 0 <= elapsed <= window_seconds


def image_to_surface(image: Image.Image) -> pygame.Surface:
    """Copy one prepared Pillow image into a display-optimized Pygame surface."""

    surface = pygame.image.frombytes(image.tobytes(), image.size, image.mode)
    if image.mode == "RGBA":
        return surface.convert_alpha()
    return surface.convert()


def current_utc_datetime() -> datetime:
    """Return an aware wall-clock instant for production UI updates."""

    return datetime.now(timezone.utc)


def localize_datetime(value: datetime, timezone_name: str) -> datetime:
    """Convert an instant to the configured zone, treating naive values as local wall time."""

    target_timezone = ZoneInfo(timezone_name)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=target_timezone)
    return value.astimezone(target_timezone)


def format_clock_time(
    value: datetime,
    clock_format: str = "12h",
    timezone_name: str = "America/New_York",
) -> str:
    """Format a datetime in the configured timezone without a 12-hour leading zero."""

    local_time = localize_datetime(value, timezone_name)
    if normalize_clock_format(clock_format) == "24h":
        return f"{local_time.hour:02d}:{local_time.minute:02d}"
    hour = local_time.hour % 12 or 12
    meridiem = "AM" if local_time.hour < 12 else "PM"
    return f"{hour}:{local_time.minute:02d} {meridiem}"


def scaled_font_size(base_size: int, display_size: Tuple[int, int]) -> int:
    """Scale a configured 1024×600 font size for another display resolution."""

    scale = min(
        display_size[0] / REFERENCE_DISPLAY_SIZE[0],
        display_size[1] / REFERENCE_DISPLAY_SIZE[1],
    )
    return max(8, round(base_size * scale))


def _split_long_word(
    word: str,
    font: pygame.font.Font,
    maximum_width: int,
) -> List[str]:
    if font.size(word)[0] <= maximum_width:
        return [word]

    chunks: List[str] = []
    current = ""
    for character in word:
        candidate = f"{current}{character}"
        if current and font.size(candidate)[0] > maximum_width:
            chunks.append(current)
            current = character
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]


def wrap_message(
    message: str,
    font: pygame.font.Font,
    maximum_width: int,
) -> List[str]:
    """Wrap message text using measured font widths."""

    if maximum_width <= 0:
        raise ValueError("maximum_width must be positive")

    lines: List[str] = []
    for paragraph in message.splitlines() or [""]:
        words = [
            chunk
            for word in paragraph.split()
            for chunk in _split_long_word(word, font, maximum_width)
        ]
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= maximum_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _ellipsize(
    line: str,
    font: pygame.font.Font,
    maximum_width: int,
) -> str:
    suffix = "…"
    shortened = line.rstrip()
    while shortened and font.size(f"{shortened}{suffix}")[0] > maximum_width:
        shortened = shortened[:-1].rstrip()
    return f"{shortened}{suffix}" if shortened else suffix


@dataclass(frozen=True)
class MessageCardLayout:
    """Rendered text and positions guaranteed to remain inside one card."""

    card_rect: pygame.Rect
    clock_surface: Optional[pygame.Surface]
    clock_position: Optional[Tuple[int, int]]
    message_surfaces: Tuple[pygame.Surface, ...]
    message_positions: Tuple[Tuple[int, int], ...]
    message_font_size: int

    @property
    def content_rects(self) -> Tuple[pygame.Rect, ...]:
        rects = [
            surface.get_rect(topleft=position)
            for surface, position in zip(self.message_surfaces, self.message_positions)
        ]
        if self.clock_surface is not None and self.clock_position is not None:
            rects.insert(0, self.clock_surface.get_rect(topleft=self.clock_position))
        return tuple(rects)


def create_message_card_layout(
    display_size: Tuple[int, int],
    message: str,
    clock_text: str,
    show_clock: bool,
    clock_font: pygame.font.Font,
    preferred_message_font_size: int,
    minimum_message_font_size: int,
    text_color: Tuple[int, int, int] = (74, 37, 50),
    clock_color: Tuple[int, int, int] = (74, 37, 50),
) -> MessageCardLayout:
    """Fit clock and message text inside a centered bottom card."""

    width, height = display_size
    scale = min(width / REFERENCE_DISPLAY_SIZE[0], height / REFERENCE_DISPLAY_SIZE[1])
    horizontal_margin = max(8, round(70 * scale))
    vertical_margin = max(8, round(30 * scale))
    padding = max(6, round(22 * scale))
    gap = max(3, round(10 * scale)) if show_clock else 0
    maximum_card_width = width - 2 * horizontal_margin
    maximum_text_width = maximum_card_width - 2 * padding
    maximum_card_height = min(
        height - 2 * vertical_margin,
        max(80, round(height * 0.48)),
    )

    clock_surface = (
        clock_font.render(clock_text, True, clock_color) if show_clock else None
    )
    clock_height = clock_surface.get_height() if clock_surface is not None else 0
    available_message_height = maximum_card_height - 2 * padding - clock_height - gap

    selected_font = pygame.font.SysFont(FONT_NAME, minimum_message_font_size)
    selected_font_size = minimum_message_font_size
    selected_lines = wrap_message(message, selected_font, maximum_text_width)
    for font_size in range(preferred_message_font_size, minimum_message_font_size - 1, -1):
        candidate_font = pygame.font.SysFont(FONT_NAME, font_size)
        candidate_lines = wrap_message(message, candidate_font, maximum_text_width)
        if len(candidate_lines) * candidate_font.get_linesize() <= available_message_height:
            selected_font = candidate_font
            selected_font_size = font_size
            selected_lines = candidate_lines
            break

    line_height = selected_font.get_linesize()
    maximum_lines = max(1, available_message_height // line_height)
    if len(selected_lines) > maximum_lines:
        selected_lines = selected_lines[:maximum_lines]
        selected_lines[-1] = _ellipsize(
            selected_lines[-1],
            selected_font,
            maximum_text_width,
        )

    message_surfaces = tuple(
        selected_font.render(line, True, text_color) for line in selected_lines
    )
    content_width = max(
        [surface.get_width() for surface in message_surfaces]
        + ([clock_surface.get_width()] if clock_surface is not None else [0])
    )
    content_height = clock_height + gap + len(message_surfaces) * line_height
    card_width = min(maximum_card_width, content_width + 2 * padding)
    card_height = min(maximum_card_height, content_height + 2 * padding)
    card_rect = pygame.Rect(
        (width - card_width) // 2,
        height - vertical_margin - card_height,
        card_width,
        card_height,
    )

    content_top = card_rect.top + padding
    clock_position: Optional[Tuple[int, int]] = None
    if clock_surface is not None:
        clock_position = (
            (width - clock_surface.get_width()) // 2,
            content_top,
        )
        content_top += clock_height + gap

    message_positions = tuple(
        ((width - surface.get_width()) // 2, content_top + index * line_height)
        for index, surface in enumerate(message_surfaces)
    )
    return MessageCardLayout(
        card_rect=card_rect,
        clock_surface=clock_surface,
        clock_position=clock_position,
        message_surfaces=message_surfaces,
        message_positions=message_positions,
        message_font_size=selected_font_size,
    )


def build_message_overlay(
    display_size: Tuple[int, int],
    message: str,
    clock_text: str,
    show_clock: bool,
    clock_font: pygame.font.Font,
    preferred_message_font_size: int,
    minimum_message_font_size: int,
    card_background_color: Tuple[int, int, int] = (239, 175, 189),
    card_opacity: int = 225,
    text_color: Tuple[int, int, int] = (74, 37, 50),
    clock_color: Tuple[int, int, int] = (74, 37, 50),
    layout: Optional[MessageCardLayout] = None,
) -> pygame.Surface:
    """Build a cached translucent card containing the clock and daily message."""

    width, height = display_size
    overlay = pygame.Surface(display_size, pygame.SRCALPHA)
    if layout is None:
        layout = create_message_card_layout(
            display_size,
            message,
            clock_text,
            show_clock,
            clock_font,
            preferred_message_font_size,
            minimum_message_font_size,
            text_color,
            clock_color,
        )

    pygame.draw.rect(
        overlay,
        (*card_background_color, card_opacity),
        layout.card_rect,
        border_radius=max(8, round(min(width, height) * 0.025)),
    )
    pygame.draw.rect(
        overlay,
        (*clock_color, min(96, card_opacity)),
        layout.card_rect,
        width=1,
        border_radius=max(8, round(min(width, height) * 0.025)),
    )

    if layout.clock_surface is not None and layout.clock_position is not None:
        overlay.blit(layout.clock_surface, layout.clock_position)
    for surface, position in zip(layout.message_surfaces, layout.message_positions):
        overlay.blit(surface, position)
    return overlay


class LoveFrameUI:
    """Pygame slideshow with touch navigation and a daily message overlay."""

    def __init__(
        self,
        config: AppConfig,
        message_provider: Optional[Callable[[], str]] = None,
        photo_loader: Optional[PhotoLoader] = None,
        prefetch_worker: Optional[PhotoPrefetchWorker] = None,
        clock: Callable[[], float] = time_module.monotonic,
        now_provider: Callable[[], datetime] = current_utc_datetime,
    ) -> None:
        self.config = config
        self.photo_loader = photo_loader or PhotoLoader(
            config.photo_path,
            output_size=(config.width, config.height),
            max_source_pixels=config.max_source_pixels,
            photo_fit=config.photo_fit,
            photo_background_color=config.photo_background_color,
        )
        self.prefetch_worker = prefetch_worker or PhotoPrefetchWorker(self.photo_loader)
        self.clock = clock
        self.now_provider = now_provider
        self._fade_duration_seconds = config.fade_duration_ms / 1_000.0
        self.message_provider = message_provider
        self.message_visible = True
        self._message = DEFAULT_MESSAGE
        self._screen: Optional[pygame.Surface] = None
        self._clock_font: Optional[pygame.font.Font] = None
        self._preferred_message_font_size = 0
        self._minimum_message_font_size = 0
        self._clock_text = ""
        self._clock_minute_key = None
        self._wall_clock_checked_at: Optional[float] = None
        self._message_overlay: Optional[pygame.Surface] = None
        self._message_layout: Optional[MessageCardLayout] = None
        self._decorations: Optional[PixelDecorationRenderer] = None
        self._current_surface: Optional[pygame.Surface] = None
        self._current_path = None
        self._photo_content_rect: Optional[Tuple[int, int, int, int]] = None
        self._transition_old: Optional[pygame.Surface] = None
        self._transition_started_at = 0.0
        self._photo_started_at = 0.0
        self._message_polled_at: Optional[float] = None
        self._last_pointer_activity_at = 0.0
        self._last_finger_action: Optional[TouchAction] = None
        self._last_finger_at: Optional[float] = None
        self._pending_navigation: Optional[TouchAction] = None
        self._cursor_visible = True

    def _default_message_provider(self, now: datetime) -> str:
        return get_daily_message(
            self.config.message_path,
            now=now,
            timezone_name=self.config.timezone_name,
            rollover_time=time(self.config.rollover_hour),
        )

    def _initialize_fonts(self) -> None:
        display_size = (self.config.width, self.config.height)
        clock_font_size = scaled_font_size(self.config.clock_font_size, display_size)
        self._preferred_message_font_size = scaled_font_size(
            self.config.message_font_size,
            display_size,
        )
        self._minimum_message_font_size = min(
            self._preferred_message_font_size,
            scaled_font_size(MINIMUM_MESSAGE_FONT_SIZE, display_size),
        )
        self._clock_font = pygame.font.SysFont(FONT_NAME, clock_font_size, bold=True)
        self._decorations = PixelDecorationRenderer(display_size, self.config)

    def run(self, max_frames: Optional[int] = None) -> int:
        """Run until quit; max_frames is used by bounded smoke tests."""

        pygame.display.init()
        pygame.font.init()
        flags = 0
        if self.config.fullscreen:
            flags = pygame.FULLSCREEN | pygame.NOFRAME

        try:
            self._screen = pygame.display.set_mode(
                (self.config.width, self.config.height),
                flags,
            )
            pygame.display.set_caption("LoveFrame")
            self._initialize_fonts()
            self.prefetch_worker.start()
            current = self.prefetch_worker.wait_for_initial()
            self._current_surface = image_to_surface(current.image)
            self._current_path = current.path
            self._photo_content_rect = current.content_rect

            now = self.clock()
            self._photo_started_at = now
            self._message_polled_at = None
            self._last_pointer_activity_at = now
            self._set_cursor_visible(True)

            frame_clock = pygame.time.Clock()
            running = True
            frames = 0
            while running:
                now = self.clock()
                running = self._handle_events(now)
                if not running:
                    break

                self._update(now)
                self._render(now)
                pygame.display.flip()
                frames += 1
                if max_frames is not None and frames >= max_frames:
                    break
                frame_clock.tick(self.config.frames_per_second)
            return 0
        finally:
            try:
                self.prefetch_worker.shutdown()
            finally:
                self.photo_loader.close()
                pygame.quit()

    def _handle_events(self, now: float) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False
            if event.type == pygame.MOUSEMOTION:
                self._record_pointer_activity(now)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if getattr(event, "touch", False):
                    continue
                action = touch_action_for_position(event.pos[0], self.config.width)
                self._record_pointer_activity(now)
                if not (
                    action is self._last_finger_action
                    and is_recent_activation(now, self._last_finger_at)
                ):
                    self._activate(action, now)
            if event.type == pygame.FINGERUP:
                action = touch_action_for_position(
                    event.x * self.config.width,
                    self.config.width,
                )
                self._last_finger_action = action
                self._last_finger_at = now
                self._activate(action, now)
        return True

    def _activate(self, action: TouchAction, now: float) -> None:
        if action is TouchAction.TOGGLE_MESSAGE:
            self.message_visible = not self.message_visible
            return
        if self._transition_old is None and self._pending_navigation is None:
            self._request_navigation(action)

    def _update(self, now: float) -> None:
        self._consume_ready_photo(now)
        message_due = (
            self._message_polled_at is None
            or now - self._message_polled_at >= self.config.message_poll_seconds
        )
        clock_due = self.config.show_clock and (
            self._wall_clock_checked_at is None
            or now - self._wall_clock_checked_at >= 1.0
        )
        overlay_changed = False
        if clock_due or message_due:
            wall_now = self.now_provider()
            if clock_due:
                overlay_changed = self._refresh_clock(wall_now)
                self._wall_clock_checked_at = now
        if message_due:
            overlay_changed = self._refresh_message(wall_now) or overlay_changed
            self._message_polled_at = now

        if overlay_changed:
            self._rebuild_message_overlay()

        if (
            now - self._photo_started_at >= self.config.slideshow_interval_seconds
            and self._transition_old is None
            and self._pending_navigation is None
        ):
            self._request_navigation(TouchAction.NEXT)

        if self._cursor_visible and cursor_should_hide(
            now,
            self._last_pointer_activity_at,
            self.config.cursor_hide_seconds,
        ):
            self._set_cursor_visible(False)

    def _request_navigation(self, action: TouchAction) -> None:
        direction = (
            NavigationDirection.PREVIOUS
            if action is TouchAction.PREVIOUS
            else NavigationDirection.NEXT
        )
        if self.prefetch_worker.request(direction):
            self._pending_navigation = action

    def _consume_ready_photo(self, now: float) -> None:
        prepared = self.prefetch_worker.take_ready()
        if prepared is None:
            return

        self._pending_navigation = None
        self._photo_started_at = now
        if prepared.path == self._current_path:
            return

        next_surface = image_to_surface(prepared.image)
        old_surface = self._current_surface
        self._current_surface = next_surface
        self._current_path = prepared.path
        self._photo_content_rect = prepared.content_rect
        self._update_decoration_layout()
        if old_surface is not None and self._fade_duration_seconds > 0:
            self._transition_old = old_surface
            self._transition_started_at = now
        else:
            self._transition_old = None

    def _refresh_clock(self, now: datetime) -> bool:
        if not self.config.show_clock:
            return False

        local_now = localize_datetime(now, self.config.timezone_name)
        minute_key = (
            local_now.year,
            local_now.month,
            local_now.day,
            local_now.hour,
            local_now.minute,
            local_now.utcoffset(),
            local_now.fold,
        )
        if minute_key == self._clock_minute_key:
            return False
        self._clock_minute_key = minute_key
        self._clock_text = format_clock_time(
            local_now,
            self.config.clock_format,
            self.config.timezone_name,
        )
        return True

    def _refresh_message(self, now: datetime) -> bool:
        try:
            message = (
                self.message_provider()
                if self.message_provider is not None
                else self._default_message_provider(now)
            )
        except Exception as error:
            LOGGER.warning("Could not refresh daily message: %s", type(error).__name__)
            return False

        if message == self._message and self._message_overlay is not None:
            return False
        self._message = message
        return True

    def _rebuild_message_overlay(self) -> None:
        if self._clock_font is None:
            return
        text_color = hex_color_to_rgb(self.config.text_color)
        clock_color = hex_color_to_rgb(self.config.clock_color)
        self._message_layout = create_message_card_layout(
            (self.config.width, self.config.height),
            self._message,
            self._clock_text,
            self.config.show_clock,
            self._clock_font,
            self._preferred_message_font_size,
            self._minimum_message_font_size,
            text_color,
            clock_color,
        )
        self._message_overlay = build_message_overlay(
            (self.config.width, self.config.height),
            self._message,
            self._clock_text,
            self.config.show_clock,
            self._clock_font,
            self._preferred_message_font_size,
            self._minimum_message_font_size,
            hex_color_to_rgb(self.config.card_background_color),
            self.config.card_opacity,
            text_color,
            clock_color,
            self._message_layout,
        )
        self._update_decoration_layout()

    def _update_decoration_layout(self) -> None:
        if self._decorations is None or self._message_layout is None:
            return
        self._decorations.update_layout(
            self._photo_content_rect,
            self._message_layout.card_rect,
            self._message_layout.content_rects,
        )

    def _render(self, now: float) -> None:
        if self._screen is None or self._current_surface is None:
            return

        progress = fade_progress(
            now,
            self._transition_started_at,
            self._fade_duration_seconds,
        )
        if self._transition_old is not None and progress < 1.0:
            self._screen.blit(self._transition_old, (0, 0))
            self._current_surface.set_alpha(round(255 * progress))
            self._screen.blit(self._current_surface, (0, 0))
            self._current_surface.set_alpha(None)
        else:
            self._transition_old = None
            self._screen.blit(self._current_surface, (0, 0))

        if self._decorations is not None:
            self._decorations.render(self._screen, now)
        if self.message_visible and self._message_overlay is not None:
            self._screen.blit(self._message_overlay, (0, 0))

    def _record_pointer_activity(self, now: float) -> None:
        self._last_pointer_activity_at = now
        self._set_cursor_visible(True)

    def _set_cursor_visible(self, visible: bool) -> None:
        if self._cursor_visible == visible:
            return
        try:
            pygame.mouse.set_visible(visible)
        except pygame.error as error:
            LOGGER.warning("Could not update pointer visibility: %s", type(error).__name__)
        self._cursor_visible = visible


def run_display(config: AppConfig) -> int:
    """Run LoveFrame and convert fatal UI errors into a logged nonzero exit."""

    try:
        return LoveFrameUI(config).run()
    except Exception as error:
        LOGGER.exception("LoveFrame display stopped: %s", type(error).__name__)
        return 1
