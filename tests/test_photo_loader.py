import random
from pathlib import Path

import pytest
from PIL import Image

import app.photo_loader as photo_loader
from app.photo_loader import PhotoLoader, create_placeholder, discover_photos, prepare_photo


def save_image(path: Path, size=(80, 60), color=(40, 80, 120), **kwargs) -> None:
    Image.new("RGB", size, color).save(path, **kwargs)


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


def test_unreadable_photo_is_skipped_without_crashing(tmp_path: Path, monkeypatch) -> None:
    unreadable = tmp_path / "unreadable.jpg"
    valid = tmp_path / "valid.jpg"
    save_image(unreadable)
    save_image(valid, color=(12, 34, 56))
    original_prepare = photo_loader.prepare_photo

    def fail_for_unreadable(path, output_size):
        if path == unreadable:
            raise PermissionError
        return original_prepare(path, output_size)

    monkeypatch.setattr(photo_loader, "prepare_photo", fail_for_unreadable)
    loader = PhotoLoader(tmp_path, rng=random.Random(3))

    assert loader.current().path == valid
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

    prepared = prepare_photo(path, (20, 40))

    top = prepared.getpixel((10, 5))
    bottom = prepared.getpixel((10, 35))
    assert top[0] > 200 and top[2] < 50
    assert bottom[2] > 200 and bottom[0] < 50


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

    prepared = prepare_photo(path, (100, 100))

    assert prepared.size == (100, 100)
    assert prepared.getpixel((50, 50))[1] > 240
    assert prepared.getpixel((0, 50))[1] > 200
    assert prepared.getpixel((99, 50))[1] > 200


def test_portrait_photo_uses_center_crop_without_stretching(tmp_path: Path) -> None:
    source = Image.new("RGB", (100, 300), "red")
    for x in range(100):
        for y in range(100, 200):
            source.putpixel((x, y), (0, 255, 0))
        for y in range(200, 300):
            source.putpixel((x, y), (0, 0, 255))
    path = tmp_path / "portrait.png"
    source.save(path)

    prepared = prepare_photo(path, (100, 100))

    assert prepared.size == (100, 100)
    assert prepared.getpixel((50, 50))[1] > 240
    assert prepared.getpixel((50, 0))[1] > 200
    assert prepared.getpixel((50, 99))[1] > 200


@pytest.mark.parametrize("source_size", [(1600, 900), (900, 1600)])
def test_prepared_output_is_exactly_1024_by_600(tmp_path: Path, source_size) -> None:
    path = tmp_path / f"photo-{source_size[0]}-{source_size[1]}.jpg"
    save_image(path, size=source_size)

    assert prepare_photo(path).size == (1024, 600)


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

    assert loader.advance().path == loader.current().path
    loader.close()


def test_loading_is_lazy_and_caches_at_most_current_and_next(
    tmp_path: Path, monkeypatch
) -> None:
    for index in range(4):
        save_image(tmp_path / f"photo-{index}.png")

    original_prepare = photo_loader.prepare_photo
    loaded_paths = []

    def recording_prepare(path, output_size):
        loaded_paths.append(path)
        return original_prepare(path, output_size)

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
