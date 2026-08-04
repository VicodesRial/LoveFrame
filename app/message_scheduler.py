"""Deterministic, offline daily-message selection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple
from zoneinfo import ZoneInfo

from app.logging_config import safe_path_label

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_ROLLOVER_TIME = time(8, 0)
DEFAULT_MESSAGE = "You are loved."


@dataclass(frozen=True)
class MessageCatalog:
    """Validated messages loaded from local JSON."""

    rotation: Tuple[str, ...] = ()
    dated: Mapping[str, str] = field(default_factory=dict)


def _valid_message(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_message_catalog(path: Path) -> MessageCatalog:
    """Load valid messages from *path* without exposing message text in logs."""

    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        LOGGER.warning(
            "Could not load message file %s: %s",
            safe_path_label(path),
            type(error).__name__,
        )
        return MessageCatalog()

    if not isinstance(raw, dict):
        LOGGER.warning(
            "Ignoring message file with a non-object root: %s",
            safe_path_label(path),
        )
        return MessageCatalog()

    rotation_raw = raw.get("rotation", [])
    rotation = (
        tuple(value.strip() for value in rotation_raw if _valid_message(value))
        if isinstance(rotation_raw, list)
        else ()
    )

    dated_raw = raw.get("dated", {})
    dated: Dict[str, str] = {}
    if isinstance(dated_raw, dict):
        for key, value in dated_raw.items():
            if not isinstance(key, str) or not _valid_message(value):
                continue
            try:
                parsed_date = date.fromisoformat(key)
            except ValueError:
                continue
            if parsed_date.isoformat() == key:
                dated[key] = value.strip()

    catalog = MessageCatalog(rotation=rotation, dated=dated)
    if not catalog.rotation and not catalog.dated:
        LOGGER.warning(
            "Message file contains no usable messages: %s",
            safe_path_label(path),
        )
    return catalog


def effective_message_date(
    now: datetime,
    timezone_name: str = DEFAULT_TIMEZONE,
    rollover_time: time = DEFAULT_ROLLOVER_TIME,
) -> date:
    """Return the effective date, changing at *rollover_time* in the target timezone.

    Aware datetimes are treated as absolute instants. Naive datetimes are interpreted as
    wall-clock time in the target timezone.
    """

    timezone = ZoneInfo(timezone_name)
    if now.tzinfo is None or now.utcoffset() is None:
        local_now = now.replace(tzinfo=timezone)
    else:
        local_now = now.astimezone(timezone)

    local_clock = local_now.time().replace(tzinfo=None)
    if local_clock < rollover_time.replace(tzinfo=None):
        return local_now.date() - timedelta(days=1)
    return local_now.date()


def select_message(catalog: MessageCatalog, effective_date: date) -> str:
    """Choose a dated message or deterministic rotating fallback."""

    dated_message = catalog.dated.get(effective_date.isoformat())
    if dated_message:
        return dated_message
    if catalog.rotation:
        return catalog.rotation[effective_date.toordinal() % len(catalog.rotation)]
    return DEFAULT_MESSAGE


def get_daily_message(
    path: Path,
    now: Optional[datetime] = None,
    timezone_name: str = DEFAULT_TIMEZONE,
    rollover_time: time = DEFAULT_ROLLOVER_TIME,
) -> str:
    """Load and select the message for the current effective date."""

    timezone = ZoneInfo(timezone_name)
    current_time = now if now is not None else datetime.now(timezone)
    effective_date = effective_message_date(current_time, timezone_name, rollover_time)
    return select_message(load_message_catalog(path), effective_date)
