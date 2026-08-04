# LoveFrame Raspberry Pi setup

This procedure installs LoveFrame on Raspberry Pi OS 64-bit with Desktop and starts it
after the `labwc` desktop logs in. Commands are labeled **Mac** or **Pi** so it is always
clear where they run.

The defaults are:

- Pi hostname: `loveframe.local`
- Pi username: `vic`
- Pi project directory: `/home/vic/LoveFrame`
- Display: 1024×600
- Timezone: `America/New_York`

Every connection value can be changed with deployment flags or the `PI_USER`, `PI_HOST`,
and `PI_PROJECT_DIR` environment variables.

## A. Flash Raspberry Pi OS

On the **Mac**, install and open Raspberry Pi Imager. Insert the microSD card and choose:

1. Device: Raspberry Pi Zero 2 W.
2. OS: the latest Raspberry Pi OS **64-bit with Desktop**, not Lite.
3. Storage: verify the exact microSD card before writing.
4. Open OS customization before starting the write.

## B. Configure the OS image

Configure these values in Imager on the **Mac**:

- Hostname: `loveframe`
- Username: `vic`
- A unique password
- The 2.4 GHz Wi-Fi network and country
- Timezone: `America/New_York`
- Keyboard layout
- SSH, using either password or public-key authentication

Enable desktop autologin. Write and verify the card, eject it safely, and insert it into
the Pi.

## C. First boot and find the Pi

With power disconnected, connect HDMI and the touchscreen USB cable. Connect power last.
Wait for the desktop to appear, then verify:

- The desktop logs in automatically.
- The display is operating at 1024×600.
- Touch input moves the pointer.
- The displayed local date and time are correct.
- The Pi responds at `loveframe.local` after it joins Wi-Fi.

Do not change rotation, calibration, HDMI, or boot settings before observing the real
hardware. Those settings vary by display revision and physical mounting.

## D. Connect from the Mac

Run on the **Mac**:

```bash
ssh vic@loveframe.local
```

Accept the host fingerprint only after confirming that it belongs to this Pi. Commands in
the resulting shell run on the **Pi**.

## E. Install runtime packages on the Pi

The first code deployment requires `rsync` on both computers. Bootstrap only the reviewed
installer from the repository on the **Mac**:

```bash
scp scripts/install_pi.sh vic@loveframe.local:/home/vic/install_loveframe.sh
```

Then connect and run on the **Pi**:

```bash
chmod 755 /home/vic/install_loveframe.sh
/home/vic/install_loveframe.sh --dry-run
/home/vic/install_loveframe.sh
```

The installer uses `apt` to install only:

- `python3`
- `python3-pygame`
- `python3-pil`
- `fonts-dejavu-core`
- `rsync`

It verifies Python, Pygame, Pillow, `zoneinfo`, and the DejaVu font. It does not use or copy
the Mac `.venv`; Debian's Pi packages supply the runtime. It creates only the LoveFrame
user state/log directory. It does not edit `/boot/firmware/config.txt`, change display or
touch settings, or enable autostart unless explicitly requested.

The temporary installer can remain for audit or be removed later by deleting only
`/home/vic/install_loveframe.sh`.

## F. Deploy the repository from the Mac

Now that the Pi has rsync, run from the repository on the **Mac**:

```bash
./scripts/deploy_to_pi.sh --dry-run
./scripts/deploy_to_pi.sh
```

The script checks SSH first and copies code with rsync. It does not use `--delete` and does
not overwrite Pi-local photos, `messages.local.json`, or `config.local.json`.

For a different Pi, use flags:

```bash
./scripts/deploy_to_pi.sh \
  --user another-user \
  --host another-host.local \
  --project-dir /home/another-user/LoveFrame
```

The destination must be absolute, cannot be `/` or `/home`, and must end in `LoveFrame`.
Use `--validate-only` to check the values and print exclusions without making an SSH
connection. Add `--smoke-test` to a real deployment for a read-only remote Python import
and source-compilation check.

## G. Transfer private content intentionally

Create these ignored files on the **Mac** if they do not already exist:

```bash
cp config/config.example.json config/config.local.json
cp data/messages.example.json data/messages.local.json
```

Put supported private photos in `assets/photos/`. Then preview the transfer:

```bash
./scripts/deploy_to_pi.sh --dry-run --include-private --yes
```

To perform it, run:

```bash
./scripts/deploy_to_pi.sh --include-private
```

The script displays a privacy warning and asks for confirmation. `--yes` is available for
an intentional noninteractive private deployment, but review the source and destination
first. Private files remain ignored by Git.

Normal later code deployments omit `--include-private` and preserve these Pi-local files.

## H. Test LoveFrame manually

Run this from a terminal inside the graphical desktop on the **Pi**:

```bash
cd /home/vic/LoveFrame
./scripts/run_pi.sh
```

`run_pi.sh` requires the private configuration and messages. For a deliberate test with
only generic tracked content:

```bash
./scripts/run_pi.sh --example-content
```

The launcher preserves the labwc Wayland environment, runs fullscreen at 1024×600, uses
system Python unbuffered, and acquires a single-instance `flock`. A second launch exits
without creating a duplicate display process.

## I. Test touchscreen controls

While LoveFrame is running on the **Pi**, test the touchscreen:

- Tap the left third for the previous photograph.
- Tap the right third for the next photograph.
- Tap the center third to hide or restore the entire clock/message card.
- Attach a keyboard temporarily and press `Esc` or `Q` to exit during testing.

## J. Enable labwc autostart

After the manual test passes, run on the **Pi**:

```bash
cd /home/vic/LoveFrame
./scripts/install_pi.sh --enable-autostart
```

This adds exactly one entry to `~/.config/labwc/autostart`:

```bash
"/home/vic/LoveFrame/scripts/run_pi.sh" &
```

If an autostart file already exists, the installer preserves its content and creates a
timestamped backup before appending. Repeated installation detects the exact entry and
does not duplicate it. The example is in `system/labwc-autostart.example`.

## K. Reboot and verify fullscreen startup

Reboot from the **Pi**:

```bash
sudo reboot
```

Verify that desktop autologin completes and LoveFrame starts fullscreen. Reboot a second
time to confirm startup is repeatable.

## L. Logs, stopping, disabling, and rollback

Application logs live on the **Pi** at:

```text
~/.local/state/loveframe/loveframe.log
```

Each file is limited to 1 MiB and three backups are retained. Logs contain lifecycle
events, filename-only content selections, skipped-photo error types, and fatal errors.
They do not contain daily-message or photograph contents.

View recent logs on the **Pi**:

```bash
tail -n 80 ~/.local/state/loveframe/loveframe.log
```

Stop LoveFrame temporarily without changing the next-login behavior:

```bash
pkill -TERM -f 'python3 -u -m app.main'
```

First stop the running application as shown above. Then edit on the **Pi**:

```bash
nano ~/.config/labwc/autostart
```

Remove only this exact line:

```bash
"/home/vic/LoveFrame/scripts/run_pi.sh" &
```

Do not delete unrelated autostart commands. To restore a timestamped backup, list the
available backups and inspect the selected file before copying it:

```bash
ls -l ~/.config/labwc/autostart.backup-*
cp ~/.config/labwc/autostart.backup-YYYYMMDD-HHMMSS \
  ~/.config/labwc/autostart
```

Replace the timestamp with the backup you inspected. This rollback changes only the user
autostart file.

For an application-code rollback, keep or check out a known-good Git revision on the Mac,
run `./scripts/deploy_to_pi.sh --dry-run`, and deploy it normally. Because deployment does
not use `--delete` and excludes private content, Pi-local photos and messages remain in
place.

## M. Run diagnostics

Run the read-only diagnostic script on the **Pi**:

```bash
cd /home/vic/LoveFrame
./scripts/pi_diagnostics.sh
```

Diagnostics report OS, kernel, architecture, Python libraries, memory, disk, temperature,
throttling, displays, Wayland variables, private-file presence, supported photo count,
process status, and recent bounded logs. Photo filenames and message contents are omitted.

## N. Hardware-dependent finishing checks

Only after observing the physical display should you adjust display rotation or touchscreen
calibration. Raspberry Pi OS, labwc, the monitor controller, and physical mounting can all
affect the required setting. LoveFrame deliberately does not automate those changes.

Before enclosing the hardware, run LoveFrame for 24 hours and verify:

- Memory use stabilizes on the 512 MB Pi.
- `vcgencmd get_throttled` reports no undervoltage or throttling history.
- Temperature remains safe.
- Touch remains aligned after reboot.
- The message changes within one minute after 08:00 America/New_York.
- The slideshow continues after Wi-Fi is disconnected.
