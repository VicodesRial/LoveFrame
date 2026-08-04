import random
import threading
from pathlib import Path

import pytest
from PIL import Image, JpegImagePlugin

import app.photo_loader as photo_loader
from app.photo_loader import (
    OversizedImageError,
    NavigationDirection,
    PhotoLoader,
    PhotoPrefetchWorker,
    PreparedPhoto,
    create_placeholder,
    discover_photos,
    prepare_photo,
)


class InOrderRandom(random.Random):
    def shuffle(self, values) -> None:
        return None


class ControlledPhotoLoader:
    """Deterministic loader whose background preparation waits for a permit."""

    def __init__(self) -> None:
        self.photos = [
            PreparedPhoto(Image.new("RGB", (10, 10), color), Path(f"{color}.jpg"))
            for color in ("red", "blue", "green")
        ]
        self._condition = threading.Condition()
        self._decode_permits = threading.Semaphore(0)
        self._current = self.photos[0]
        self._next = None
        self.prepare_calls = 0
        self.advance_calls = 0
        self.active_decodes = 0
        self.maximum_active_decodes = 0

    @property
    def cached_image_count(self) -> int:
        with self._condition:
            return len(
                {
                    id(photo.image)
                    for photo in (self._current, self._next)
                    if photo is not None
                }
            )

    def current(self) -> PreparedPhoto:
        return self._current

    def prepare_next(self) -> PreparedPhoto:
        with self._condition:
            self.prepare_calls += 1
            call_number = self.prepare_calls
            self.active_decodes += 1
            self.maximum_active_decodes = max(
                self.maximum_active_decodes,
                self.active_decodes,
            )
            self._condition.notify_all()

        self._decode_permits.acquire()
        prepared = self.photos[min(call_number, len(self.photos) - 1)]
        with self._condition:
            self._next = prepared
            self.active_decodes -= 1
            self._condition.notify_all()
        return prepared

    def advance(self) -> PreparedPhoto:
        with self._condition:
            assert self._next is not None
            self.advance_calls += 1
            self._current = self._next
            self._next = None
            self._condition.notify_all()
            return self._current

    def previous(self) -> PreparedPhoto:
        return self._current

    def release_decode(self) -> None:
        self._decode_permits.release()

    def wait_for(self, predicate) -> None:
        with self._condition:
            assert self._condition.wait_for(predicate, timeout=2.0)

    def close(self) -> None:
        for photo in self.photos:
            photo.image.close()


def save_image(path: Path, size=(80, 60), color=(40, 80, 120), **kwargs) -> None:
    image = Image.new("RGB", size, color)
    try:
        image.save(path, **kwargs)
    finally:
        image.close()


def test_discovers_supported_extensions_case_insensitively(tmp_path: Path) -> None:
    supported = ["one.jpg", "two.JPEG", "three.png", "four.WEBP"]
    for name in supported:
        save_image(tmp_path / name)

    assert {path.name for path in discover_photos(tmp_path)} == set(supported)


def test_ignores_hidden_unsupported_and_temporary_files(tmp_path: Path) -> None:
    for name in ["visible.jpg", ".hidden.jpg", "~working.jpg", "photo.tmp.jpg", "photo.part.jpg"]:
        save_image(tmp_path / name)
    save_image(tmp_path / "unsupported.gif")
    (tmp_path / "notes.txt").write_text("not a photo", encoding="utf-8")
    (tmp_path / "folder.jpg").mkdir()

    assert discover_photos(tmp_path) == (tmp_path / "visible.jpg",)


def test_missing_or_empty_directory_has_no_discovered_photos(tmp_path: Path) -> None:
    assert discover_photos(tmp_path) == ()
    assert discover_photos(tmp_path / "missing") == ()


def test_placeholder_is_generated_at_requested_dimensions() -> None:
    placeholder = create_placeholder((1024, 600))

    assert placeholder.size == (1024, 600)
    assert placeholder.mode == "RGB"


def test_empty_directory_returns_placeholder(tmp_path: Path) -> None:
    loader = PhotoLoader(tmp_path)

    current = loader.current()

    assert current.is_placeholder
    assert current.image.size == (1024, 600)
    assert loader.cached_image_count == 1
    loader.close()


def test_corrupt_photo_is_skipped_when_valid_photo_exists(tmp_path: Path) -> None:
    (tmp_path / "corrupt.jpg").write_bytes(b"not an image")
    save_image(tmp_path / "valid.png", color=(12, 34, 56))
    loader = PhotoLoader(tmp_path, rng=random.Random(3))

    current = loader.current()

    assert current.path == tmp_path / "valid.png"
    assert current.image.getpixel((512, 300)) == (12, 34, 56)
    loader.close()


def test_unreadable_photo_is_skipped_without_crashing(
    tmp_path: Path, monkeypatch, caplog
) -> None:
    unreadable = tmp_path / "unreadable.jpg"
    valid = tmp_path / "valid.jpg"
    save_image(unreadable)
    save_image(valid, color=(12, 34, 56))
    original_prepare = photo_loader.prepare_photo
    attempted = []

    def fail_for_unreadable(
        path, output_size, max_source_pixels, photo_fit, photo_background_color
    ):
        attempted.append(path)
        if path == unreadable:
            raise PermissionError
        return original_prepare(
            path,
            output_size,
            max_source_pixels,
            photo_fit,
            photo_background_color,
        )

    monkeypatch.setattr(photo_loader, "prepare_photo", fail_for_unreadable)
    loader = PhotoLoader(tmp_path, rng=InOrderRandom())

    assert loader.current().path == valid
    assert attempted == [unreadable, valid]
    assert len(caplog.records) == 1
    assert "PermissionError" in caplog.text
    loader.close()


@pytest.mark.parametrize(
    "error_type",
    [Image.DecompressionBombError, Image.DecompressionBombWarning],
)
def test_decompression_bomb_is_skipped(
    tmp_path: Path, monkeypatch, caplog, error_type
) -> None:
    bomb = tmp_path / "a-bomb.jpg"
    valid = tmp_path / "b-valid.jpg"
    save_image(bomb)
    save_image(valid)
    original_prepare = photo_loader.prepare_photo

    def fail_for_bomb(
        path, output_size, max_source_pixels, photo_fit, photo_background_color
    ):
        if path == bomb:
            raise error_type("unsafe dimensions")
        return original_prepare(
            path,
            output_size,
            max_source_pixels,
            photo_fit,
            photo_background_color,
        )

    monkeypatch.setattr(photo_loader, "prepare_photo", fail_for_bomb)
    loader = PhotoLoader(tmp_path, rng=InOrderRandom())

    assert loader.current().path == valid
    assert len(caplog.records) == 1
    assert error_type.__name__ in caplog.text
    loader.close()


def test_oversized_image_is_rejected_before_expensive_transforms(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "oversized.jpg"
    path.write_bytes(b"header is mocked")

    class HeaderOnlyImage:
        size = (5_000, 5_000)
        format = "JPEG"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def getexif(self):
            pytest.fail("EXIF must not be read for an oversized image")

        def draft(self, *args):
            pytest.fail("draft must not run for an oversized image")

    monkeypatch.setattr(photo_loader.Image, "open", lambda unused: HeaderOnlyImage())
    monkeypatch.setattr(
        photo_loader.ImageOps,
        "exif_transpose",
        lambda unused: pytest.fail("oversized image must not be transposed"),
    )

    with pytest.raises(OversizedImageError):
        prepare_photo(path)


def test_configured_pixel_limit_skips_oversized_image_with_one_warning(
    tmp_path: Path, caplog
) -> None:
    oversized = tmp_path / "a-oversized.jpg"
    valid = tmp_path / "b-valid.jpg"
    save_image(oversized, size=(80, 60))
    save_image(valid, size=(10, 10))
    loader = PhotoLoader(
        tmp_path,
        max_source_pixels=200,
        rng=InOrderRandom(),
    )

    assert loader.current().path == valid
    assert len(caplog.records) == 1
    assert "OversizedImageError" in caplog.text
    loader.close()


def test_all_corrupt_photos_return_placeholder(tmp_path: Path, caplog) -> None:
    (tmp_path / "corrupt.jpg").write_bytes(b"not an image")

    current = PhotoLoader(tmp_path).current()

    assert current.is_placeholder
    assert "Skipping unreadable photo" in caplog.text


def test_all_corrupt_photos_reuse_placeholder_for_prefetch(tmp_path: Path) -> None:
    (tmp_path / "corrupt.jpg").write_bytes(b"not an image")
    loader = PhotoLoader(tmp_path)

    current = loader.current()

    assert loader.prepare_next() is current
    assert loader.cached_image_count == 1
    loader.close()


def test_exif_orientation_is_applied_before_resize(tmp_path: Path) -> None:
    source = Image.new("RGB", (40, 20), "red")
    for x in range(20, 40):
        for y in range(20):
            source.putpixel((x, y), (0, 0, 255))
    exif = source.getexif()
    exif[274] = 6
    path = tmp_path / "rotated.jpg"
    source.save(path, exif=exif, quality=100, subsampling=0)
    source.close()

    prepared = prepare_photo(path, (20, 40))

    top = prepared.getpixel((10, 5))
    bottom = prepared.getpixel((10, 35))
    assert top[0] > 200 and top[2] < 50
    assert bottom[2] > 200 and bottom[0] < 50
    prepared.close()


@pytest.mark.parametrize(
    ("source_size", "expected_target"),
    [
        ((4032, 3024), (800, 600)),
        ((6000, 1200), (1024, 205)),
    ],
)
def test_large_jpeg_uses_aspect_aware_decoder_downsampling(
    tmp_path: Path, monkeypatch, source_size, expected_target
) -> None:
    path = tmp_path / f"photo-{source_size[0]}-{source_size[1]}.jpg"
    save_image(path, size=source_size)
    original_draft = JpegImagePlugin.JpegImageFile.draft
    draft_calls = []

    def recording_draft(image, mode, target):
        result = original_draft(image, mode, target)
        draft_calls.append((target, image.size))
        return result

    monkeypatch.setattr(JpegImagePlugin.JpegImageFile, "draft", recording_draft)

    prepared = prepare_photo(path)

    assert prepared.size == (1024, 600)
    assert draft_calls[0][0] == expected_target
    assert draft_calls[0][1][0] * draft_calls[0][1][1] < source_size[0] * source_size[1]
    prepared.close()


def test_contain_blur_centers_complete_portrait_without_distortion(
    tmp_path: Path,
) -> None:
    source = Image.new("RGB", (40, 100))
    source.paste((255, 0, 0), (0, 0, 20, 50))
    source.paste((0, 255, 0), (20, 0, 40, 50))
    source.paste((0, 0, 255), (0, 50, 20, 100))
    source.paste((255, 255, 0), (20, 50, 40, 100))
    path = tmp_path / "four-corners.png"
    source.save(path)
    source.close()

    prepared = prepare_photo(path, (120, 80), photo_fit="contain_blur")

    assert prepared.size == (120, 80)
    foreground_bounds = (44, 0, 76, 80)
    assert (foreground_bounds[2] - foreground_bounds[0]) / 80 == pytest.approx(0.4)
    assert prepared.getpixel((48, 10))[0] > 240
    assert prepared.getpixel((72, 10))[1] > 240
    assert prepared.getpixel((48, 70))[2] > 240
    bottom_right = prepared.getpixel((72, 70))
    assert bottom_right[0] > 240 and bottom_right[1] > 240
    assert sum(prepared.getpixel((10, 20))) < sum(prepared.getpixel((48, 20)))
    prepared.close()


def test_contain_color_adds_pink_side_bars_and_preserves_entire_portrait(
    tmp_path: Path,
) -> None:
    source = Image.new("RGB", (40, 100))
    source.paste((255, 0, 0), (0, 0, 20, 50))
    source.paste((0, 255, 0), (20, 0, 40, 50))
    source.paste((0, 0, 255), (0, 50, 20, 100))
    source.paste((255, 255, 0), (20, 50, 40, 100))
    path = tmp_path / "portrait.png"
    source.save(path)
    source.close()

    prepared = prepare_photo(path, (120, 80), photo_fit="contain_color")

    assert prepared.getpixel((0, 40)) == (248, 221, 227)
    assert prepared.getpixel((119, 40)) == (248, 221, 227)
    assert prepared.getpixel((48, 10))[0] > 240
    assert prepared.getpixel((72, 10))[1] > 240
    assert prepared.getpixel((48, 70))[2] > 240
    bottom_right = prepared.getpixel((72, 70))
    assert bottom_right[0] > 240 and bottom_right[1] > 240
    assert 32 / 80 == pytest.approx(40 / 100)
    assert prepared.info["loveframe_content_rect"] == (44, 0, 32, 80)
    prepared.close()


def test_loader_transfers_contained_photo_bounds_without_retaining_source(
    tmp_path: Path,
) -> None:
    path = tmp_path / "portrait.png"
    save_image(path, size=(40, 100))
    loader = PhotoLoader(tmp_path, output_size=(120, 80), rng=InOrderRandom())

    current = loader.current()

    assert current.content_rect == (44, 0, 32, 80)
    assert loader.cached_image_count == 1
    loader.close()


def test_contain_color_adds_custom_top_and_bottom_bars_to_wide_photo(
    tmp_path: Path,
) -> None:
    path = tmp_path / "wide.png"
    save_image(path, size=(100, 40), color=(12, 90, 180))

    prepared = prepare_photo(
        path,
        (80, 80),
        photo_fit="contain_color",
        photo_background_color="#ABCDEF",
    )

    assert prepared.getpixel((40, 0)) == (171, 205, 239)
    assert prepared.getpixel((40, 79)) == (171, 205, 239)
    assert prepared.getpixel((40, 24)) == (12, 90, 180)
    assert prepared.getpixel((40, 55)) == (12, 90, 180)
    assert 80 / 32 == pytest.approx(100 / 40)
    prepared.close()


def test_contain_color_does_not_run_blur_processing(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "photo.png"
    save_image(path, size=(40, 100))

    def fail_blur(*args, **kwargs):
        raise AssertionError("contain_color must not invoke Gaussian blur")

    monkeypatch.setattr(Image.Image, "filter", fail_blur)

    prepared = prepare_photo(path, (120, 80), photo_fit="contain_color")

    assert prepared.size == (120, 80)
    prepared.close()


def test_invalid_direct_photo_fit_falls_back_to_contain_color(tmp_path: Path) -> None:
    save_image(tmp_path / "photo.png", size=(40, 100))
    loader = PhotoLoader(tmp_path, output_size=(120, 80), photo_fit="stretch")

    assert loader.photo_fit == "contain_color"
    assert loader.current().image.size == (120, 80)
    loader.close()


def test_contain_blur_prefetch_composition_runs_in_worker(
    tmp_path: Path, monkeypatch
) -> None:
    save_image(tmp_path / "a.png", size=(80, 120))
    save_image(tmp_path / "b.png", size=(120, 80))
    original_compose = photo_loader._compose_contain_blur
    worker_composed = threading.Event()

    def record_composition(image, output_size):
        if threading.current_thread().name == "loveframe-photo-prefetch":
            worker_composed.set()
        return original_compose(image, output_size)

    monkeypatch.setattr(photo_loader, "_compose_contain_blur", record_composition)
    loader = PhotoLoader(
        tmp_path,
        output_size=(120, 80),
        photo_fit="contain_blur",
        rng=InOrderRandom(),
    )
    worker = PhotoPrefetchWorker(loader)
    worker.start()

    assert worker_composed.wait(timeout=2.0)
    assert worker.wait_for_initial().image.size == (120, 80)
    worker.shutdown()
    assert loader.cached_image_count <= 2
    loader.close()


def test_landscape_photo_uses_center_crop_without_stretching(tmp_path: Path) -> None:
    source = Image.new("RGB", (300, 100), "red")
    for x in range(100, 200):
        for y in range(100):
            source.putpixel((x, y), (0, 255, 0))
    for x in range(200, 300):
        for y in range(100):
            source.putpixel((x, y), (0, 0, 255))
    path = tmp_path / "landscape.png"
    source.save(path)
    source.close()

    prepared = prepare_photo(path, (100, 100), photo_fit="cover")

    assert prepared.size == (100, 100)
    assert prepared.getpixel((50, 50))[1] > 240
    assert prepared.getpixel((0, 50))[1] > 200
    assert prepared.getpixel((99, 50))[1] > 200
    prepared.close()


def test_portrait_photo_uses_center_crop_without_stretching(tmp_path: Path) -> None:
    source = Image.new("RGB", (100, 300), "red")
    for x in range(100):
        for y in range(100, 200):
            source.putpixel((x, y), (0, 255, 0))
        for y in range(200, 300):
            source.putpixel((x, y), (0, 0, 255))
    path = tmp_path / "portrait.png"
    source.save(path)
    source.close()

    prepared = prepare_photo(path, (100, 100), photo_fit="cover")

    assert prepared.size == (100, 100)
    assert prepared.getpixel((50, 50))[1] > 240
    assert prepared.getpixel((50, 0))[1] > 200
    assert prepared.getpixel((50, 99))[1] > 200
    prepared.close()


@pytest.mark.parametrize(
    "source_size",
    [(1600, 900), (900, 1600), (800, 800), (2000, 300), (300, 2000)],
)
def test_prepared_output_is_exactly_1024_by_600(tmp_path: Path, source_size) -> None:
    path = tmp_path / f"photo-{source_size[0]}-{source_size[1]}.jpg"
    save_image(path, size=source_size)

    prepared = prepare_photo(path)

    assert prepared.size == (1024, 600)
    prepared.close()


def test_shuffle_does_not_immediately_repeat_when_alternative_exists(tmp_path: Path) -> None:
    for index in range(3):
        save_image(tmp_path / f"photo-{index}.png", color=(index * 40, 0, 0))
    loader = PhotoLoader(tmp_path, output_size=(100, 60), rng=random.Random(7))

    paths = [loader.current().path]
    for _ in range(12):
        paths.append(loader.advance().path)

    assert all(previous != current for previous, current in zip(paths, paths[1:]))
    loader.close()


def test_single_valid_photo_can_repeat(tmp_path: Path) -> None:
    save_image(tmp_path / "only.png")
    loader = PhotoLoader(tmp_path, output_size=(100, 60))

    current = loader.current()
    following = loader.prepare_next()

    assert following is current
    assert loader.cached_image_count == 1
    assert loader.advance() is current
    loader.close()


def test_previous_reloads_history_without_retaining_extra_images(tmp_path: Path) -> None:
    for name in ("a.png", "b.png", "c.png"):
        save_image(tmp_path / name)
    loader = PhotoLoader(
        tmp_path,
        output_size=(100, 60),
        rng=InOrderRandom(),
    )

    assert loader.current().path == tmp_path / "a.png"
    assert loader.advance().path == tmp_path / "b.png"
    loader.prepare_next()
    assert loader.cached_image_count == 2

    assert loader.previous().path == tmp_path / "a.png"
    assert loader.cached_image_count == 1
    loader.close()


def test_loading_is_lazy_and_caches_at_most_current_and_next(
    tmp_path: Path, monkeypatch
) -> None:
    for index in range(4):
        save_image(tmp_path / f"photo-{index}.png")

    original_prepare = photo_loader.prepare_photo
    loaded_paths = []

    def recording_prepare(
        path, output_size, max_source_pixels, photo_fit, photo_background_color
    ):
        loaded_paths.append(path)
        return original_prepare(
            path,
            output_size,
            max_source_pixels,
            photo_fit,
            photo_background_color,
        )

    monkeypatch.setattr(photo_loader, "prepare_photo", recording_prepare)
    loader = PhotoLoader(tmp_path, output_size=(100, 60), rng=random.Random(11))

    assert loaded_paths == []
    assert loader.cached_image_count == 0

    current = loader.current()
    assert len(loaded_paths) == 1
    assert loader.current() is current
    assert len(loaded_paths) == 1
    assert loader.cached_image_count == 1

    following = loader.prepare_next()
    assert len(loaded_paths) == 2
    assert loader.prepare_next() is following
    assert len(loaded_paths) == 2
    assert loader.cached_image_count == 2

    assert loader.advance() is following
    assert loader.cached_image_count == 1
    loader.close()


def test_prefetch_worker_is_nonblocking_bounded_and_replenishes_cache() -> None:
    loader = ControlledPhotoLoader()
    worker = PhotoPrefetchWorker(loader)
    worker.start()
    loader.wait_for(lambda: loader.prepare_calls == 1)

    assert loader.active_decodes == 1
    assert loader.cached_image_count == 1
    assert worker.request(NavigationDirection.NEXT) is True
    assert worker.request(NavigationDirection.NEXT) is False
    assert loader.maximum_active_decodes == 1

    loader.release_decode()
    loader.wait_for(lambda: loader.prepare_calls == 2)
    ready = worker.take_ready()

    assert ready is loader.photos[1]
    assert loader.advance_calls == 1
    assert loader.active_decodes == 1
    assert loader.cached_image_count == 1

    loader.release_decode()
    loader.wait_for(lambda: loader.active_decodes == 0)
    assert loader.cached_image_count == 2
    assert loader.maximum_active_decodes == 1

    worker.shutdown()
    assert worker.is_alive is False
    loader.close()
