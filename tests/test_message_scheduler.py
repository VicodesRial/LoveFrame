import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.message_scheduler import (
    DEFAULT_MESSAGE,
    MessageCatalog,
    effective_message_date,
    get_daily_message,
    load_message_catalog,
    select_message,
)

NEW_YORK = ZoneInfo("America/New_York")


def test_rollover_changes_at_exactly_eight_am() -> None:
    assert effective_message_date(datetime(2026, 6, 10, 7, 59, tzinfo=NEW_YORK)) == date(
        2026, 6, 9
    )
    assert effective_message_date(datetime(2026, 6, 10, 8, 0, tzinfo=NEW_YORK)) == date(
        2026, 6, 10
    )


def test_naive_datetime_is_interpreted_as_new_york_wall_time() -> None:
    assert effective_message_date(datetime(2026, 6, 10, 7, 59)) == date(2026, 6, 9)
    assert effective_message_date(datetime(2026, 6, 10, 8, 0)) == date(2026, 6, 10)


def test_utc_datetime_is_converted_to_new_york() -> None:
    assert effective_message_date(datetime(2026, 6, 10, 11, 59, tzinfo=timezone.utc)) == date(
        2026, 6, 9
    )
    assert effective_message_date(datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)) == date(
        2026, 6, 10
    )


@pytest.mark.parametrize(
    ("utc_value", "expected"),
    [
        (datetime(2026, 3, 8, 11, 59, tzinfo=timezone.utc), date(2026, 3, 7)),
        (datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc), date(2026, 3, 8)),
        (datetime(2026, 11, 1, 12, 59, tzinfo=timezone.utc), date(2026, 10, 31)),
        (datetime(2026, 11, 1, 13, 0, tzinfo=timezone.utc), date(2026, 11, 1)),
    ],
)
def test_dst_transition_dates_use_new_york_eight_am(
    utc_value: datetime, expected: date
) -> None:
    assert effective_message_date(utc_value) == expected


def test_custom_rollover_time() -> None:
    value = datetime(2026, 6, 10, 8, 29, tzinfo=NEW_YORK)
    assert effective_message_date(value, rollover_time=time(8, 30)) == date(2026, 6, 9)


def test_dated_message_overrides_rotation() -> None:
    catalog = MessageCatalog(
        rotation=("first", "second"),
        dated={"2026-09-14": "date-specific"},
    )

    assert select_message(catalog, date(2026, 9, 14)) == "date-specific"


def test_dated_messages_follow_effective_date_across_rollover(tmp_path: Path) -> None:
    path = tmp_path / "messages.json"
    path.write_text(
        json.dumps(
            {
                "rotation": ["rotation"],
                "dated": {
                    "2026-09-13": "yesterday dated",
                    "2026-09-14": "today dated",
                },
            }
        ),
        encoding="utf-8",
    )

    assert get_daily_message(path, datetime(2026, 9, 14, 7, 59, tzinfo=NEW_YORK)) == (
        "yesterday dated"
    )
    assert get_daily_message(path, datetime(2026, 9, 14, 8, 0, tzinfo=NEW_YORK)) == (
        "today dated"
    )


def test_rotation_is_deterministic_and_advances_daily() -> None:
    catalog = MessageCatalog(rotation=("zero", "one", "two"), dated={})
    first_date = date(2026, 6, 10)
    second_date = date(2026, 6, 11)

    expected_first = catalog.rotation[first_date.toordinal() % len(catalog.rotation)]
    expected_second = catalog.rotation[second_date.toordinal() % len(catalog.rotation)]
    assert select_message(catalog, first_date) == expected_first
    assert select_message(catalog, first_date) == expected_first
    assert select_message(catalog, second_date) == expected_second
    assert expected_first != expected_second


def test_get_daily_message_is_stable_across_reloads(tmp_path: Path) -> None:
    path = tmp_path / "messages.json"
    path.write_text(json.dumps({"rotation": ["first", "second"], "dated": {}}))
    now = datetime(2026, 6, 10, 9, 0, tzinfo=NEW_YORK)

    assert get_daily_message(path, now) == get_daily_message(path, now)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "{invalid json",
        "[]",
        "null",
        "{}",
        '{"rotation": [], "dated": {}}',
    ],
)
def test_invalid_or_empty_content_returns_fallback(
    tmp_path: Path, content: str, caplog
) -> None:
    path = tmp_path / "messages.json"
    path.write_text(content, encoding="utf-8")

    assert get_daily_message(path, datetime(2026, 6, 10, 9, 0, tzinfo=NEW_YORK)) == DEFAULT_MESSAGE
    assert caplog.records


def test_missing_file_returns_fallback(tmp_path: Path, caplog) -> None:
    path = tmp_path / "missing.json"

    assert get_daily_message(path, datetime(2026, 6, 10, 9, 0, tzinfo=NEW_YORK)) == DEFAULT_MESSAGE
    assert "Could not load message file" in caplog.text


def test_unreadable_file_returns_fallback(tmp_path: Path, monkeypatch, caplog) -> None:
    path = tmp_path / "messages.json"
    path.write_text("{}", encoding="utf-8")

    def raise_permission_error(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(Path, "read_text", raise_permission_error)

    assert load_message_catalog(path) == MessageCatalog()
    assert "Could not load message file" in caplog.text


def test_partially_invalid_content_keeps_valid_entries(tmp_path: Path) -> None:
    path = tmp_path / "messages.json"
    path.write_text(
        json.dumps(
            {
                "rotation": [" valid rotation ", "", None, 17],
                "dated": {
                    "2026-09-14": " valid dated ",
                    "2026-02-30": "invalid date",
                    "not-a-date": "invalid key",
                    "2026-09-15": " ",
                    "2026-09-16": 42,
                },
            }
        ),
        encoding="utf-8",
    )

    catalog = load_message_catalog(path)

    assert catalog.rotation == ("valid rotation",)
    assert catalog.dated == {"2026-09-14": "valid dated"}


def test_wrong_collection_shapes_are_treated_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "messages.json"
    path.write_text(
        json.dumps({"rotation": "not a list", "dated": ["not", "an", "object"]}),
        encoding="utf-8",
    )

    assert load_message_catalog(path) == MessageCatalog()


def test_logs_do_not_include_private_message_text(tmp_path: Path, caplog) -> None:
    private_text = "private-secret-message"
    path = tmp_path / "messages.json"
    path.write_text(json.dumps({"rotation": [private_text], "dated": {}}), encoding="utf-8")

    load_message_catalog(path)

    assert private_text not in caplog.text
