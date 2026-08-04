# LoveFrame release checklist

This checklist separates completed Mac/software work from the Phase F work that must be
performed on the real Raspberry Pi and display. Do not mark a hardware item complete without
recording the observation from the actual device.

## Completed software and Mac checks

- [x] Software Phases A–E implemented.
- [x] Complete automated test suite passed in headless SDL mode.
- [x] Python source compilation passed.
- [x] Shell syntax, JSON examples, executable bits, deployment validation, privacy ignores,
  and tracked-file credential scan passed.
- [x] Comprehensive software audit completed after the timezone correction.
- [x] Malformed timezone values safely fall back to `America/New_York` without private input
  appearing in logs.
- [x] Private photos, messages, and local configuration are excluded from Git.
- [x] Mac Pygame acceptance completed at 1024×600, including photo shapes, empty content,
  message lengths, theme, decorations, fades, controls, rapid navigation, cursor hiding, and
  clean exit.

## GitHub release preparation

- [ ] Pull request from `agent/phase-c-photo-loader` into `main` is open and checks are green.
- [ ] Pull request review is complete.
- [ ] Pull request is merged into `main`.
- [ ] Local and remote `main` contain the release commit.

## Raspberry Pi provisioning and deployment

- [ ] Flash and verify Raspberry Pi OS 64-bit with Desktop on the intended SD card.
- [ ] Complete first boot and confirm the desktop is 1024×600.
- [ ] Confirm SSH access using the expected host fingerprint.
- [ ] Run the installer with `--dry-run`, then run the installer normally.
- [ ] Run deployment with `--dry-run`, then deploy normally.
- [ ] Launch once with `./scripts/run_pi.sh --example-content`.
- [ ] Transfer private content intentionally with `--include-private`.
- [ ] Launch normally and confirm missing private files are not accepted.

## Pi interaction and startup

- [ ] Verify physical left, right, and center touchscreen zones.
- [ ] Verify cursor hiding and fullscreen presentation without desktop chrome.
- [ ] Enable labwc autostart only after the manual launch passes.
- [ ] Reboot once and confirm automatic startup.
- [ ] Reboot a second time and confirm automatic startup remains reliable.
- [ ] Send SIGTERM, confirm clean shutdown, and confirm the `flock` lock is released.
- [ ] Confirm a duplicate launch is rejected while LoveFrame is already running.
- [ ] Run `./scripts/pi_diagnostics.sh` and save the non-private results.

## Reliability and final hardware work

- [ ] Complete a 24-hour Pi reliability run with stable memory use.
- [ ] Confirm offline photo rotation and message display with Wi-Fi disconnected.
- [ ] Observe the daily message changing within one minute after 08:00
  `America/New_York`.
- [ ] Confirm no undervoltage, throttling, overheating, touch disconnects, or random restarts.
- [ ] Load and verify final private photos, messages, important dates, and Mac backups.
- [ ] Measure the actual display, Pi case, hub, ports, and cable clearances.
- [ ] Build and fit-test the enclosure without blocking ventilation or touch areas.
- [ ] Repeat reboot, touch, Wi-Fi, power, and thermal checks inside the final enclosure.
