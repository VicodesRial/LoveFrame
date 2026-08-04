"""Low-memory photo discovery and preparation for LoveFrame."""

from __future__ import annotations

import logging
import math
import random
import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Deque, List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

from app.config import (
    DEFAULT_PHOTO_BACKGROUND_COLOR,
    DEFAULT_PHOTO_FIT,
    hex_color_to_rgb,
    normalize_hex_color,
    normalize_photo_fit,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT_SIZE = (1024, 600)
DEFAULT_MAX_SOURCE_PIXELS = 20_000_000
SUPPORTED_EXTENSIONS = frozenset({".jpeg", ".jpg", ".png", ".webp"})
ROTATED_EXIF_ORIENTATIONS = frozenset({5, 6, 7, 8})


class OversizedImageError(ValueError):
    """Raised before decoding when an image exceeds the configured pixel limit."""


class NavigationDirection(Enum):
    """Direction requested from the background photo worker."""

    PREVIOUS = "previous"
    NEXT = "next"


def _is_temporary_name(name: str) -> bool:
    lowered = name.casefold()
    return (
        lowered.startswith("~")
        or lowered.startswith(".#")
        or lowered.endswith("~")
        or ".tmp." in lowered
        or ".part." in lowered
    )


def discover_photos(directory: Path) -> Tuple[Path, ...]:
    """Return supported, visible photo paths without opening image contents."""

    directory = Path(directory)
    try:
        entries = directory.iterdir()
        photos = [
            entry
            for entry in entries
            if entry.is_file()
            and not entry.name.startswith(".")
            and not _is_temporary_name(entry.name)
            and entry.suffix.casefold() in SUPPORTED_EXTENSIONS
        ]
    except OSError as error:
        LOGGER.warning("Could not scan photo directory: %s", type(error).__name__)
        return ()
    return tuple(sorted(photos, key=lambda path: path.name.casefold()))


def prepare_photo(
    path: Path,
    output_size: Tuple[int, int] = DEFAULT_OUTPUT_SIZE,
    max_source_pixels: int = DEFAULT_MAX_SOURCE_PIXELS,
    photo_fit: str = DEFAULT_PHOTO_FIT,
    photo_background_color: str = DEFAULT_PHOTO_BACKGROUND_COLOR,
) -> Image.Image:
    """Open, orient, and compose one photo at the exact display dimensions."""

    width, height = output_size
    if width <= 0 or height <= 0:
        raise ValueError("output dimensions must be positive")
    if (
        not isinstance(max_source_pixels, int)
        or isinstance(max_source_pixels, bool)
        or max_source_pixels <= 0
    ):
        raise ValueError("max_source_pixels must be a positive integer")
    photo_fit = normalize_photo_fit(photo_fit)
    photo_background_color = normalize_hex_color(
        photo_background_color,
        DEFAULT_PHOTO_BACKGROUND_COLOR,
    )

    with Image.open(path) as source:
        source_width, source_height = source.size
        if source_width <= 0 or source_height <= 0:
            raise ValueError("source image dimensions must be positive")
        source_pixels = source_width * source_height
        if source_pixels > max_source_pixels:
            raise OversizedImageError(
                f"source image exceeds {max_source_pixels} pixels"
            )

        orientation = source.getexif().get(274, 1)
        target_width, target_height = output_size
        if orientation in ROTATED_EXIF_ORIENTATIONS:
            target_width, target_height = target_height, target_width

        # Preserve the source aspect ratio in the hint so Pillow can choose native JPEG
        # decoder downsampling while retaining enough pixels for the selected fit mode.
        scale_for_output = min if photo_fit == "contain_color" else max
        fill_scale = scale_for_output(
            target_width / source_width,
            target_height / source_height,
        )
        decode_target = (
            max(1, math.ceil(source_width * fill_scale)),
            max(1, math.ceil(source_height * fill_scale)),
        )
        if source.format == "JPEG":
            source.draft("RGB", decode_target)

        oriented = ImageOps.exif_transpose(source)
        try:
            converted = oriented.convert("RGB")
            try:
                if photo_fit == "cover":
                    prepared = _compose_cover(converted, output_size)
                elif photo_fit == "contain_blur":
                    prepared = _compose_contain_blur(converted, output_size)
                else:
                    prepared = _compose_contain_color(
                        converted,
                        output_size,
                        hex_color_to_rgb(photo_background_color),
                    )
                prepared.load()
                return prepared
            finally:
                converted.close()
        finally:
            if oriented is not source:
                oriented.close()


def _compose_cover(image: Image.Image, output_size: Tuple[int, int]) -> Image.Image:
    """Center-crop an image to fill the output without distortion."""

    return ImageOps.fit(
        image,
        output_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def _compose_contain_blur(
    image: Image.Image,
    output_size: Tuple[int, int],
) -> Image.Image:
    """Place the complete image over a blurred, darkened crop of itself."""

    background = _compose_cover(image, output_size)
    try:
        blur_radius = max(4.0, min(output_size) / 30.0)
        blurred = background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    finally:
        background.close()

    try:
        composition = ImageEnhance.Brightness(blurred).enhance(0.68)
    finally:
        blurred.close()

    try:
        foreground = ImageOps.contain(
            image,
            output_size,
            method=Image.Resampling.LANCZOS,
        )
    except Exception:
        composition.close()
        raise
    try:
        left = (output_size[0] - foreground.width) // 2
        top = (output_size[1] - foreground.height) // 2
        composition.paste(foreground, (left, top))
    except Exception:
        composition.close()
        raise
    finally:
        foreground.close()
    return composition


def _compose_contain_color(
    image: Image.Image,
    output_size: Tuple[int, int],
    background_color: Tuple[int, int, int],
) -> Image.Image:
    """Center the complete image over a solid color without cropping or distortion."""

    composition = Image.new("RGB", output_size, color=background_color)
    try:
        foreground = ImageOps.contain(
            image,
            output_size,
            method=Image.Resampling.LANCZOS,
        )
    except Exception:
        composition.close()
        raise
    try:
        left = (output_size[0] - foreground.width) // 2
        top = (output_size[1] - foreground.height) // 2
        composition.paste(foreground, (left, top))
        composition.info["loveframe_content_rect"] = (
            left,
            top,
            foreground.width,
            foreground.height,
        )
    except Exception:
        composition.close()
        raise
    finally:
        foreground.close()
    return composition


def create_placeholder(
    output_size: Tuple[int, int] = DEFAULT_OUTPUT_SIZE,
) -> Image.Image:
    """Generate an in-memory placeholder when no usable photo is available."""

    width, height = output_size
    if width <= 0 or height <= 0:
        raise ValueError("output dimensions must be positive")

    image = Image.new("RGB", output_size, color=(25, 20, 32))
    draw = ImageDraw.Draw(image)
    margin = max(12, min(width, height) // 12)
    draw.rounded_rectangle(
        (margin, margin, width - margin - 1, height - margin - 1),
        radius=max(8, margin // 2),
        outline=(111, 80, 128),
        width=max(2, margin // 12),
    )
    message = "Add photos to assets/photos"
    bounds = draw.textbbox((0, 0), message)
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    draw.text(
        ((width - text_width) // 2, (height - text_height) // 2),
        message,
        fill=(235, 225, 240),
    )
    return image


@dataclass(frozen=True)
class PreparedPhoto:
    """A prepared display image and its source, if one exists."""

    image: Image.Image
    path: Optional[Path]
    content_rect: Optional[Tuple[int, int, int, int]] = None

    @property
    def is_placeholder(self) -> bool:
        return self.path is None


class PhotoLoader:
    """Lazily prepare photos while retaining no more than current and next images."""

    def __init__(
        self,
        directory: Path,
        output_size: Tuple[int, int] = DEFAULT_OUTPUT_SIZE,
        max_source_pixels: int = DEFAULT_MAX_SOURCE_PIXELS,
        photo_fit: str = DEFAULT_PHOTO_FIT,
        photo_background_color: str = DEFAULT_PHOTO_BACKGROUND_COLOR,
        rng: Optional[random.Random] = None,
    ) -> None:
        if output_size[0] <= 0 or output_size[1] <= 0:
            raise ValueError("output dimensions must be positive")
        if (
            not isinstance(max_source_pixels, int)
            or isinstance(max_source_pixels, bool)
            or max_source_pixels <= 0
        ):
            raise ValueError("max_source_pixels must be a positive integer")
        self.directory = Path(directory)
        self.output_size = output_size
        self.max_source_pixels = max_source_pixels
        self.photo_fit = normalize_photo_fit(photo_fit)
        self.photo_background_color = normalize_hex_color(
            photo_background_color,
            DEFAULT_PHOTO_BACKGROUND_COLOR,
        )
        self.paths: Tuple[Path, ...] = discover_photos(self.directory)
        self._rng = rng if rng is not None else random.Random()
        self._invalid_paths: Set[Path] = set()
        self._history: Deque[Path] = deque(maxlen=max(1, len(self.paths)))
        self._current: Optional[PreparedPhoto] = None
        self._next: Optional[PreparedPhoto] = None
        self._lock = threading.RLock()

    @property
    def cached_image_count(self) -> int:
        """Return the number of distinct prepared images retained in memory."""

        with self._lock:
            return len(
                {
                    id(photo.image)
                    for photo in (self._current, self._next)
                    if photo is not None
                }
            )

    def current(self) -> PreparedPhoto:
        """Return the current photo, decoding it only on first access."""

        with self._lock:
            if self._current is None:
                self._current = self._load_candidate()
            return self._current

    def prepare_next(self) -> PreparedPhoto:
        """Prepare and cache one next photo without repeating a valid alternative."""

        with self._lock:
            if self._next is None:
                current = self.current()
                if current.is_placeholder and all(
                    path in self._invalid_paths for path in self.paths
                ):
                    self._next = current
                else:
                    self._next = self._load_candidate(
                        exclude=current.path,
                        fallback=current,
                    )
            return self._next

    def advance(self) -> PreparedPhoto:
        """Promote the prepared next photo and release the previous image."""

        with self._lock:
            previous = self.current()
            following = self.prepare_next()
            if (
                previous.path is not None
                and following.path is not None
                and previous.path != following.path
            ):
                self._history.append(previous.path)
            self._current = following
            self._next = None
            if previous.image is not following.image:
                previous.image.close()
            return following

    def previous(self) -> PreparedPhoto:
        """Reload the previous valid path without retaining its decoded image."""

        with self._lock:
            current = self.current()
            while self._history:
                path = self._history.pop()
                preceding = self._prepare_path(path)
                if preceding is None:
                    continue

                prefetched = self._next
                self._next = None
                self._current = preceding
                if prefetched is not None and prefetched.image is not current.image:
                    prefetched.image.close()
                if current.image is not preceding.image:
                    current.image.close()
                return preceding
            return current

    def close(self) -> None:
        """Release all prepared image memory owned by this loader."""

        with self._lock:
            images = {
                id(photo.image): photo.image
                for photo in (self._current, self._next)
                if photo is not None
            }
            for image in images.values():
                image.close()
            self._current = None
            self._next = None

    def _load_candidate(
        self,
        exclude: Optional[Path] = None,
        fallback: Optional[PreparedPhoto] = None,
    ) -> PreparedPhoto:
        candidates: List[Path] = [
            path
            for path in self.paths
            if path not in self._invalid_paths and path != exclude
        ]
        self._rng.shuffle(candidates)

        for path in candidates:
            prepared = self._prepare_path(path)
            if prepared is not None:
                return prepared

        if (
            fallback is not None
            and fallback.path == exclude
            and exclude not in self._invalid_paths
        ):
            return fallback

        return PreparedPhoto(image=create_placeholder(self.output_size), path=None)

    def _prepare_path(self, path: Path) -> Optional[PreparedPhoto]:
        try:
            image = prepare_photo(
                path,
                self.output_size,
                self.max_source_pixels,
                self.photo_fit,
                self.photo_background_color,
            )
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            OSError,
            SyntaxError,
            ValueError,
            UnidentifiedImageError,
        ) as error:
            self._invalid_paths.add(path)
            LOGGER.warning("Skipping unreadable photo: %s", type(error).__name__)
            return None
        content_rect = image.info.get("loveframe_content_rect")
        return PreparedPhoto(image=image, path=path, content_rect=content_rect)


class PhotoPrefetchWorker:
    """Own background preparation with one request and one result slot."""

    def __init__(self, loader: PhotoLoader) -> None:
        self.loader = loader
        self._condition = threading.Condition()
        self._initial: Optional[PreparedPhoto] = None
        self._request: Optional[NavigationDirection] = None
        self._ready: Optional[PreparedPhoto] = None
        self._stopping = False
        self._started = False
        self._failed = False
        self._thread = threading.Thread(
            target=self._run,
            name="loveframe-photo-prefetch",
            daemon=True,
        )

    @property
    def is_alive(self) -> bool:
        """Return whether the worker thread is running."""

        return self._thread.is_alive()

    def start(self) -> None:
        """Start the single worker and its initial one-photo prefetch."""

        with self._condition:
            if self._started:
                return
            self._started = True
            self._thread.start()

    def request(self, direction: NavigationDirection) -> bool:
        """Queue one navigation request without blocking or growing a task queue."""

        with self._condition:
            if (
                not self._started
                or self._stopping
                or self._failed
                or self._request is not None
                or self._ready is not None
            ):
                return False
            self._request = direction
            self._condition.notify_all()
            return True

    def wait_for_initial(self) -> PreparedPhoto:
        """Wait during startup for the worker's first prepared composition."""

        with self._condition:
            if not self._started:
                raise RuntimeError("Photo prefetch worker has not started")
            while self._initial is None and not self._failed and not self._stopping:
                self._condition.wait()
            if self._initial is not None:
                return self._initial
            raise RuntimeError("Photo prefetch worker failed during startup")

    def take_ready(self) -> Optional[PreparedPhoto]:
        """Transfer a promoted photo to the main thread without waiting."""

        with self._condition:
            prepared = self._ready
            self._ready = None
            if prepared is not None:
                self._condition.notify_all()
            return prepared

    def shutdown(self) -> None:
        """Request worker termination and join it before loader cleanup."""

        with self._condition:
            if not self._started:
                return
            self._stopping = True
            self._condition.notify_all()
        self._thread.join()

    def _run(self) -> None:
        try:
            initial = self.loader.current()
            with self._condition:
                if self._stopping:
                    return
                self._initial = initial
                self._condition.notify_all()

            self.loader.prepare_next()
            while True:
                with self._condition:
                    while not self._stopping and self._request is None:
                        self._condition.wait()
                    if self._stopping:
                        return
                    direction = self._request
                    self._request = None

                if direction is NavigationDirection.PREVIOUS:
                    prepared = self.loader.previous()
                else:
                    prepared = self.loader.advance()

                with self._condition:
                    if self._stopping:
                        return
                    self._ready = prepared
                    self._condition.notify_all()

                self.loader.prepare_next()
        except Exception as error:
            LOGGER.exception("Photo prefetch worker stopped: %s", type(error).__name__)
            with self._condition:
                self._failed = True
                self._condition.notify_all()
