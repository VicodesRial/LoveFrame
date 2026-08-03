# LoveFrame

LoveFrame is a lightweight, offline photo display for a Raspberry Pi Zero 2 W and a
1024×600 HDMI/USB touchscreen. The finished application will show a fullscreen photo
carousel and one daily message, with touch navigation and an 08:00 America/New_York
message rollover.

This checkpoint contains Phases A and B only: project configuration and the deterministic
daily-message scheduler. Photo loading, Pygame rendering, touch controls, Pi autostart,
and deployment scripts are intentionally deferred to later phases.

## Requirements

- Python 3.9 or newer
- Local timezone data containing `America/New_York`
- No internet connection is required after dependencies are installed

Create a development environment on macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Private local content

Tracked example files contain only generic text. To use private content later, copy the
examples and edit only the ignored copies:

```bash
cp config/config.example.json config/config.local.json
cp data/messages.example.json data/messages.local.json
```

Then set `messages.path` in `config/config.local.json` to
`data/messages.local.json`. Real photos belong in `assets/photos/`. Git ignores all three
private locations.

The message file shape is:

```json
{
  "rotation": ["A general message"],
  "dated": {"2026-09-14": "A message for this date"}
}
```

Invalid entries are ignored while valid entries remain usable. If no usable message is
available, the scheduler returns `You are loved.` and logs a warning without logging
private message text.

## Daily scheduling

The effective message date changes at 08:00 in `America/New_York`:

- Before 08:00, the effective date is yesterday.
- At and after 08:00, the effective date is today.
- A dated message overrides the rotation list.
- Otherwise, selection uses `effective_date.toordinal() % len(rotation)`, so it is stable
  across restarts and works offline.

Aware datetimes are converted to New York as absolute instants. Naive datetimes are
interpreted as New York wall-clock time. Production callers should pass aware datetimes.

## Run the current checkpoint

Print the current example message:

```bash
python -m app.main --messages data/messages.example.json
```

Use local configuration and its configured message path:

```bash
python -m app.main --config config/config.local.json
```

An ISO timestamp can be supplied for a deterministic check:

```bash
python -m app.main --messages data/messages.example.json --at 2026-09-14T08:00:00-04:00
```

Run all tests:

```bash
python -m pytest
```

The current CLI prints a message only; it is not the photo-frame interface. The photo
loader and Pygame UI will be added in Phases C and D.
