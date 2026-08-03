"""Low-memory photo discovery and preparation for LoveFrame."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT_SIZE = (1024, 600)
SUPPORTED_EXTENSIONS = frozenset({".jpeg", ".jpg", ".png", ".webp"})


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
) -> Image.Image:
    """Open one photo, apply EXIF orientation, and center-crop it to fill the output."""

    width, height = output_size
    if width <= 0 or height <= 0:
        raise ValueError("output dimensions must be positive")

    with Image.open(path) as source:
        # JPEG decoders may use a reduced native resolution, lowering peak memory for large
        # camera files while retaining ample detail for the 1024×600 display.
        draft_size = max(width, height) * 2
        source.draft("RGB", (draft_size, draft_size))
        oriented = ImageOps.exif_transpose(source)
        try:
            converted = oriented.convert("RGB")
            try:
                prepared = ImageOps.fit(
                    converted,
                    output_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                prepared.load()
                return prepared
            finally:
                converted.close()
        finally:
            if oriented is not source:
                oriented.close()


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

    @property
    def is_placeholder(self) -> bool:
        return self.path is None


class PhotoLoader:
    """Lazily prepare photos while retaining no more than current and next images."""

    def __init__(
        self,
        directory: Path,
        output_size: Tuple[int, int] = DEFAULT_OUTPUT_SIZE,
        rng: Optional[random.Random] = None,
    ) -> None:
        if output_size[0] <= 0 or output_size[1] <= 0:
            raise ValueError("output dimensions must be positive")
        self.directory = Path(directory)
        self.output_size = output_size
        self.paths: Tuple[Path, ...] = discover_photos(self.directory)
        self._rng = rng if rng is not None else random.Random()
        self._invalid_paths: Set[Path] = set()
        self._current: Optional[PreparedPhoto] = None
        self._next: Optional[PreparedPhoto] = None

    @property
    def cached_image_count(self) -> int:
        """Return the number of distinct prepared images retained in memory."""

        return len(
            {
                id(photo.image)
                for photo in (self._current, self._next)
                if photo is not None
            }
        )

    def current(self) -> PreparedPhoto:
        """Return the current photo, decoding it only on first access."""

        if self._current is None:
            self._current = self._load_candidate()
        return self._current

    def prepare_next(self) -> PreparedPhoto:
        """Prepare and cache one next photo without repeating a valid alternative."""

        if self._next is None:
            current = self.current()
            if current.is_placeholder and all(
                path in self._invalid_paths for path in self.paths
            ):
                self._next = current
            else:
                self._next = self._load_candidate(exclude=current.path)
        return self._next

    def advance(self) -> PreparedPhoto:
        """Promote the prepared next photo and release the previous image."""

        previous = self.current()
        following = self.prepare_next()
        self._current = following
        self._next = None
        if previous.image is not following.image:
            previous.image.close()
        return following

    def close(self) -> None:
        """Release all prepared image memory owned by this loader."""

        images = {
            id(photo.image): photo.image
            for photo in (self._current, self._next)
            if photo is not None
        }
        for image in images.values():
            image.close()
        self._current = None
        self._next = None

    def _load_candidate(self, exclude: Optional[Path] = None) -> PreparedPhoto:
        candidates: List[Path] = [
            path
            for path in self.paths
            if path not in self._invalid_paths and path != exclude
        ]
        self._rng.shuffle(candidates)

        # Reuse the current path only when no other valid candidate can be loaded.
        if exclude is not None and exclude not in self._invalid_paths:
            candidates.append(exclude)

        for path in candidates:
            try:
                image = prepare_photo(path, self.output_size)
            except (OSError, SyntaxError, ValueError, UnidentifiedImageError) as error:
                self._invalid_paths.add(path)
                LOGGER.warning("Skipping unreadable photo: %s", type(error).__name__)
                continue
            return PreparedPhoto(image=image, path=path)

        return PreparedPhoto(image=create_placeholder(self.output_size), path=None)
