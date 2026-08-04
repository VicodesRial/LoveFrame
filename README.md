# LoveFrame

LoveFrame is a lightweight, offline photo display for a Raspberry Pi Zero 2 W and a
1024×600 HDMI/USB touchscreen. The finished application will show a fullscreen photo
carousel and one daily message, with touch navigation and an 08:00 America/New_York
message rollover.

This checkpoint contains Phases A through D: project configuration, the deterministic
daily-message scheduler, a low-memory Pillow photo pipeline, and the Pygame display.
Pi autostart and deployment scripts are intentionally deferred to Phase E.

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

## Photo pipeline

`app.photo_loader.PhotoLoader` discovers JPEG, JPG, PNG, and WEBP files in one directory
without decoding them. It ignores hidden, unsupported, and temporary files. Images are
decoded only when requested and corrected using EXIF orientation.

The default `photos.photo_fit` setting is `contain_color`. It centers the complete,
aspect-preserving photograph over a solid pastel-pink background without stretching,
cropping, or blur. Portrait photos receive side bars and wide photos receive top and bottom
bars. Set it to `contain_blur` for the earlier blurred-photo background or `cover` for the
original centered crop-to-fill behavior. Invalid values safely use `contain_color`.

The default background is `#F8DDE3`. Any standard six-digit `#RRGGBB` value can be set with
`photos.photo_background_color`. Contain-color composition happens in the existing photo
worker and retains only its final display-sized result; it does not run Gaussian blur.

The loader retains only the current prepared image and an optional prefetched next image.
Calling `advance()` releases the previous Pillow image. Corrupt or unreadable files are
skipped, and an in-memory placeholder is generated when no usable photo is available.
Callers should not retain prepared images after advancing the loader and should call
`close()` during shutdown.

The display owns one background photo worker. It prepares the initial current and next
photos, performs fit-mode composition and navigation promotion, and replenishes the single
next-image cache. The main thread only receives completed 1024×600 Pillow compositions and
creates Pygame surfaces, so touch handling and automatic rotation never wait for image
decoding or blur processing. The worker has one request slot and one result slot rather than
an unbounded task queue, and it is joined before loader shutdown.

Before decoding, the loader rejects sources above 20,000,000 pixels by default. This cap
is configurable through `PhotoLoader(max_source_pixels=...)` without changing Pillow's
global decompression-bomb protection. JPEG files within the limit use aspect-aware native
decoder downsampling before EXIF correction and RGB conversion to reduce peak memory.
Resize unusually large photos before copying them to the Pi instead of raising the limit.

## Pygame display

The display changes photos every 15 seconds by default, polls the daily message once per
minute, and uses a short cached fade. Touch or click the left third for the previous photo,
the right third for the next photo, and the center third to hide or show the message. Press
`Esc` or `Q` to exit during development. The pointer hides after three seconds of inactivity.
Slideshow intervals, message polling, fades, cursor inactivity, and pointer-event
deduplication all use injectable monotonic seconds, so wall-clock changes and long runtimes
cannot strand a timer.

The translucent pastel-pink card shows the configured local time above the daily message.
It uses 12-hour time without a leading zero by default; set `messages.clock_format` to
`24h` for 24-hour time or `messages.show_clock` to `false` to hide the clock. Clock and
message font sizes default to 34 and 25 pixels at 1024×600 and scale proportionally at
other resolutions.
Long messages progressively shrink to a documented 16-pixel reference minimum, also
scaled with the display. Content that is still too long at that minimum is safely
ellipsized rather than extending beyond the card. The overlay is rebuilt only when the
localized minute or daily message changes.

Theme colors accept standard six-digit hexadecimal values. Invalid colors and opacity
values safely return to the palette below. The card remains a separate cached Pygame
overlay, so changing its theme does not require photographs to be decoded again.

```json
"photos": {
  "photo_fit": "contain_color",
  "photo_background_color": "#F8DDE3"
},
"messages": {
  "show_clock": true,
  "clock_format": "12h",
  "clock_font_size": 34,
  "message_font_size": 25,
  "card_background_color": "#EFAFBD",
  "card_opacity": 225,
  "text_color": "#4A2532",
  "clock_color": "#4A2532"
},
"decorations": {
  "show_decorations": true,
  "decoration_style": "pixel_hearts",
  "heart_color": "#D85B7B",
  "heart_highlight_color": "#FFF0F4",
  "sparkle_color": "#C94F70",
  "animate_decorations": true,
  "decoration_density": "medium"
}
```

Pixel-art hearts, outlined hearts, diamonds, dotted trails, and four-point sparkles are drawn
procedurally from integer-aligned Pygame rectangles; no emoji or image assets are used.
`medium` is the default and produces up to 18 motifs across two sufficiently large bars.
`low` preserves the sparse four-motif arrangement. `high` adds at most approximately 30%
more small motifs than the medium layout. Invalid density values still use the safe `low`
fallback, and invalid colors return to the documented palette.

Separate deterministic asymmetric templates fill vertical sidebars and horizontal bars.
Their motif budget scales with each bar's actual area, so narrow bars automatically receive
fewer decorations. Every motif stays inside its pink bar and outside an expanded message-card
exclusion zone; unsafe lower-priority motifs are omitted. Photos without usable bars retain
the sparse corner fallback. Only medium and large hearts use the three-frame monotonic pulse;
small hearts, outlines, diamonds, trails, and sparkles stay static. No decoration surface is
rebuilt during ordinary frame rendering.

Run windowed on macOS:

```bash
python -m app.main --windowed
```

Run borderless fullscreen on the Raspberry Pi:

```bash
python -m app.main --fullscreen
```

Command-line `--photos` and `--messages` options override their configured paths. Display,
slideshow, photo-memory, and message-poll settings are documented in
`config/config.example.json`.

## Message diagnostic

Print the current example message:

```bash
python -m app.main --print-message --messages data/messages.example.json
```

Use local configuration and its configured message path:

```bash
python -m app.main --print-message --config config/config.local.json
```

An ISO timestamp can be supplied for a deterministic check:

```bash
python -m app.main --print-message --messages data/messages.example.json \
  --at 2026-09-14T08:00:00-04:00
```

Run all tests:

```bash
python -m pytest
```

The interface remains fully offline after its Python dependencies and private local content
have been installed.
