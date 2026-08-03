# LoveFrame repository instructions

## Target

- Raspberry Pi Zero 2 W with a 1 GHz quad-core CPU and 512 MB RAM.
- Raspberry Pi OS 64-bit with Desktop and `labwc`.
- Eyoyo EM07KD HDMI/USB touchscreen at 1024×600.

## Technical constraints

- Use Python 3, Pygame, Pillow, pytest, and the standard library.
- Do not add Chromium, Electron, Node.js, Docker, databases, cloud storage, or AI APIs.
- Keep the finished display fully functional without internet access.
- Never preload every full-resolution photo. Retain at most the current and next decoded image.
- Handle missing, empty, invalid, and corrupted photo or message files without crashing.
- Keep macOS development windowed and Raspberry Pi production borderless fullscreen.

## Privacy

- Never commit real personal photos, private messages, or local configuration.
- Store private content only in ignored `assets/photos/`, `data/messages.local.json`, and
  `config/config.local.json` paths.
- Use generic example content and generated fixtures in tracked files and tests.
- Do not include private message text in logs or test failure messages.

## Quality

- Add tests for the 08:00 America/New_York rollover, DST behavior, dated messages,
  deterministic fallback rotation, empty content, and corrupt files.
- Consider null, empty, invalid, and boundary inputs for every content-loading change.
- Run the full test suite and `git diff --check` before declaring work complete.
- Preserve low CPU and memory use appropriate for 512 MB RAM.

## Raspberry Pi deployment

- Do not make destructive system changes.
- Do not modify boot, desktop, or system files without documenting the exact change and rollback.
- Installation and deployment scripts must be idempotent and must not overwrite private content.
- Keep development dependencies and virtual environments out of Pi deployments.

## Definition of done

- The finished app starts after a cold boot, displays crop-to-fill photos without distortion,
  and responds to previous, next, and message-visibility touch zones.
- The message changes within one minute after 08:00 America/New_York and survives restarts.
- Missing or corrupt content does not crash the display, and the app works without Wi-Fi.
- A 24-hour Pi test shows no crash, memory growth, overheating, or undervoltage.
