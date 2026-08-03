# LoveFrame: Raspberry Pi Zero 2 W Photo Display

> Complete shopping list, Codex setup, build roadmap, Raspberry Pi installation guide, and final enclosure plan.

## Project goal

Build an Alexa/Echo Show-style desktop display that:

- Shows a full-screen carousel of photos of you and your girlfriend.
- Displays one lovely message per day.
- Changes the daily message at approximately **8:00 a.m. America/New_York time**.
- Works locally without a subscription, cloud service, or AI API.
- Starts automatically whenever the Raspberry Pi is powered on.
- Can be updated from your Mac over Wi-Fi.
- Uses a custom black wedge enclosure so the finished project resembles an Echo Show.

## Important hardware decision

This guide uses:

- Your **Raspberry Pi Zero 2 W**.
- A new **HDMI + USB touchscreen**.
- A lightweight native Python/Pygame application.

Your existing **Freenove FNK0078A 5-inch screen cannot connect to the Raspberry Pi Zero 2 W**. It uses the MIPI DSI interface, and the Zero 2 W does not have a DSI connector. Keep it for a future Pi 3/4/5 project, return it, or sell it.

The Zero 2 W has 512 MB of RAM. Raspberry Pi's current Chromium kiosk tutorial recommends at least 1 GB, so this project will **not** use a Chromium kiosk. Pygame gives us a smoother, lighter photo frame on this hardware.

---

# 1. Inventory

## Items you already own

- [x] Raspberry Pi Zero 2 W
- [x] Passive heatsinks installed on the Pi
- [x] Official Raspberry Pi Zero case and lids
- [x] Samsung EVO Select 128 GB microSD card
- [x] Full-size SD adapter
- [x] MakerSpot micro-USB OTG hub
- [x] Mini-HDMI male to HDMI female adapter
- [x] Small screwdriver and some screen mounting hardware
- [x] Freenove FNK0078A 5-inch DSI touchscreen — **not compatible with the Zero 2 W**

## Buy now

| Priority | Item | Recommended option | Expected price | Notes |
|---|---|---|---:|---|
| Required | HDMI/USB touchscreen | [Eyoyo EM07KD 7-inch 1024×600 touchscreen](https://www.amazon.com/dp/B0F9NWWG9L) | About $45.99 | Supports Raspberry Pi Zero through HDMI. Includes a Mini-HDMI-to-HDMI cable, USB touch cable, stand, adapter, and screws. |
| Required unless you already have an appropriate supply | Pi power supply | [Official Raspberry Pi 12.5W Micro-USB supply — Micro Center](https://www.microcenter.com/product/643086/raspberry-pi-125-watt-power-supply) | About $7.99 | Official 5.1V/2.5A supply for the Zero 2 W. Select the Miami store and verify stock before driving. |
| Alternate seller | Pi power supply | [Official Raspberry Pi 12.5W supply — PiShop.us](https://www.pishop.us/product/raspberry-pi-12-5w-power-supply-us-white/) | About $8.80 | Use if Micro Center is unavailable. |

### Check an existing 15W adapter before buying the official supply

You may use an existing adapter only if all of these are true:

- [ ] Its output label states **5V DC** and at least **2.5A**; 5V/3A is also acceptable.
- [ ] It uses a safe, good-quality Micro-USB cable or has a captive Micro-USB cable.
- [ ] It does not rely on a higher USB-C Power Delivery voltage.
- [ ] The Pi shows no low-voltage warning or random restarts during testing.

The official supply remains the least troublesome option.

## Buy or obtain after the electronics work

| Item | Option | Purpose |
|---|---|---|
| Custom Alexa-style enclosure | Print at [FIU Honors EdgeLab](https://honorsedgelab.fiu.edu/) or [FIU Engineering MakerSpace](https://makerspace.fiu.edu/) | Holds the screen, Pi, hub, and cables in a clean wedge-shaped body. |
| Online print alternative | [Craftcloud upload and quote](https://craftcloud3d.com/en/upload) | Use if FIU printing is unavailable. |
| Industrial hook-and-loop strips | [Walmart VELCRO Industrial Strength](https://www.walmart.com/ip/VELCRO-Brand-VEL90199-Industrial-Strength-Indoor-Outdoor-Use-Superior-Holding-Power-on-Smooth-Surfaces-Black-4in-x-2in-Strips/19311524) | Secures the Pi case or hub during the prototype stage. Never attach adhesive directly to the bare Pi board. |
| Cable management | [Dollar Tree cable-management kit](https://sameday.dollartree.com/store/dollar-tree/products/103484293-e-circuit-assorted-cable-management-kit-7-ct) | Organizes cables behind or inside the enclosure. |
| Cable ties | [Dollar Tree 100-count cable ties](https://www.dollartree.com/tool-bench-hardware-assorted-nylon-cable-ties-100ct-packs/186612) | Bundles extra cable length. |
| Rubber/felt feet | [Dollar Tree felt protectors](https://www.dollartree.com/tool-bench-felt-protectors/243661) | Stops the enclosure from sliding or scratching furniture. |
| Cheap prototype material | [Dollar Tree black foam board](https://www.dollartree.com/black-foam-boards-20x30-in/25957) | Optional temporary Echo Show-style wedge before 3D printing. |

## Buy only if testing proves it is necessary

- [ ] **Powered USB hub:** Only buy one if the screen/touch connection causes low-voltage warnings, touch disconnects, or random restarts. First test your existing MakerSpot hub with the official Pi supply.
- [ ] **USB-C SD-card reader:** Only needed if your Mac has no full-size SD slot. Your microSD card already includes a full-size adapter.
- [ ] **M2.5 screws/standoffs:** Wait until the enclosure CAD file specifies exact lengths.
- [ ] **Extension cord or surge protector:** Only if the final placement requires it. Use a UL- or ETL-listed product.

## Do not buy

- [ ] Another microSD card
- [ ] Another Pi Zero case
- [ ] Another Mini-HDMI adapter
- [ ] A GPIO header or soldering equipment
- [ ] A Chromium kiosk kit
- [ ] A generic “7-inch Raspberry Pi case” before checking exact screen dimensions
- [ ] Another DSI screen for the Zero 2 W

## Budget

- Required screen + official supply: approximately **$53.98 before tax**.
- Cosmetic supplies: approximately **$3–$10**.
- 3D-printed enclosure: potentially free/low-cost at FIU; online price depends on the final model and material.
- Keep a **$20 contingency**, but do not spend it until hardware testing identifies a real need.

---

# 2. Finished system design

## Hardware connections

1. Official power supply → Pi port labeled **PWR IN**.
2. Included Mini-HDMI-to-HDMI cable → Pi Mini-HDMI port → Eyoyo HDMI input.
3. MakerSpot hub → Pi port labeled **USB**, not PWR IN.
4. Eyoyo USB touch cable → MakerSpot hub.
5. microSD card → Pi microSD slot.

During prototype testing, keep the Pi in its existing case behind the monitor. Do not block the heatsinks or ventilation.

## Software architecture

- **Operating system:** Raspberry Pi OS 64-bit with Desktop.
- **Application:** Python 3 + Pygame + Pillow.
- **Storage:** Photos and messages stored locally on the microSD card.
- **Daily update:** The app checks the local time once per minute.
- **Automatic startup:** Raspberry Pi desktop auto-login plus `labwc` autostart.
- **Development:** Codex on your Mac, then deploy to the Pi over SSH.
- **Internet:** Needed for setup and remote updates, but not required for the slideshow after installation.

## Daily message behavior

The app should calculate an “effective message date”:

- Before 8:00 a.m.: use yesterday’s message.
- At or after 8:00 a.m.: use today’s message.
- Check once every 60 seconds.
- If the Pi is off at exactly 8:00 a.m., switch immediately after the next boot.
- Prefer a message explicitly assigned to a calendar date.
- Otherwise rotate through the general message list without failing.

This is more reliable than a scheduled script because the correct message appears even after a restart or network outage.

---

# 3. Prepare content

## Photos

- [ ] Choose an initial set of 30–100 photos.
- [ ] Export them from Photos/iCloud to a folder on your Mac.
- [ ] Use JPEG or PNG files.
- [ ] Remove screenshots, duplicates, and blurry photos.
- [ ] Include a mix of landscape and portrait photos.
- [ ] Keep originals backed up elsewhere.
- [ ] Do not publish the photo folder to a public GitHub repository.

The application should crop photos to fill 1024×600 without stretching faces. It should load only the current and next image into memory, not every full-resolution photo at once.

## Lovely messages

- [ ] Write at least 30 messages so repetition is not immediate.
- [ ] Add birthdays, anniversaries, trips, or other date-specific messages.
- [ ] Keep private messages in `data/messages.local.json`.
- [ ] Put only example messages in the Git repository.

Suggested JSON shape:

```json
{
  "rotation": [
    "I hope today is as lovely as you are.",
    "Thank you for making ordinary days feel special.",
    "I love every little life we are building together."
  ],
  "dated": {
    "2026-09-14": "Happy anniversary, my love ❤️",
    "2026-12-25": "My favorite gift is getting to share life with you."
  }
}
```

---

# 4. Set up the project in Codex

Official OpenAI documentation says Codex can work on a selected local folder, and a repository-level `AGENTS.md` is loaded automatically as project guidance:

- [Codex/ChatGPT quickstart](https://learn.chatgpt.com/docs/quickstart)
- [Codex `AGENTS.md` documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex best practices](https://learn.chatgpt.com/guides/best-practices)

## Create the project folder on your Mac

Open Terminal and run:

```bash
mkdir -p ~/Developer/love-frame
cd ~/Developer/love-frame
git init
```

Then place this file in the folder as:

```text
LOVE_FRAME_PROJECT_GUIDE.md
```

## Open it in Codex

### Recommended: ChatGPT desktop app

- [ ] Open the ChatGPT desktop app.
- [ ] Select **Codex**.
- [ ] Choose **Open folder**.
- [ ] Select `~/Developer/love-frame`.
- [ ] Confirm Codex has permission to read and write only this project folder.

### Optional: Codex CLI

Follow the [official Codex CLI quickstart](https://developers.openai.com/codex/cli), open Terminal in the repository, and run:

```bash
cd ~/Developer/love-frame
codex
```

Keep the default permissions initially. Review every command and diff while learning the workflow.

## First Codex prompt

Paste this exactly:

```text
Read LOVE_FRAME_PROJECT_GUIDE.md completely. We are building LoveFrame for a Raspberry Pi Zero 2 W with 512 MB RAM and a 1024x600 HDMI/USB touchscreen.

Before writing code:
1. Restate the architecture and constraints.
2. Propose the final repository tree.
3. Identify anything that would be too resource-heavy for the Zero 2 W.
4. Create a task plan mapped to the guide's checklists.
5. Do not implement anything until I approve the plan.
```

## Create `AGENTS.md`

After approving the plan, ask Codex:

```text
Create a concise repository-level AGENTS.md using the project rules in LOVE_FRAME_PROJECT_GUIDE.md. It must specify the target hardware, low-memory constraints, required tests, privacy rules for photos/messages, Pi deployment rules, and definition of done. Show me the file before continuing.
```

The file should capture these rules:

```markdown
# LoveFrame repository instructions

## Target

- Raspberry Pi Zero 2 W: 1 GHz quad-core CPU and 512 MB RAM.
- Raspberry Pi OS 64-bit with Desktop and labwc.
- Eyoyo EM07KD HDMI/USB touchscreen at 1024×600.

## Technical constraints

- Use Python 3, Pygame, Pillow, and the standard library.
- Do not use Chromium, Electron, Node, Docker, a database, or a cloud dependency for the MVP.
- Never preload every full-resolution photo into memory.
- The display must continue working without internet.
- Handle corrupt/missing image and message files gracefully.

## Privacy

- Never commit real photos or private messages.
- Keep private content in ignored local files.
- Provide example content for tests and documentation.

## Quality

- Add tests for the 8:00 a.m. message rollover, date-specific messages, fallback rotation, empty content, and corrupt files.
- Run tests and formatting before declaring a task complete.
- Keep Mac development mode windowed and Pi production mode fullscreen.
- Do not modify Raspberry Pi boot or system files without documenting the exact change and rollback.

## Definition of done

- Starts automatically after a cold boot.
- Displays photos without distortion.
- Changes the message within one minute after 8:00 a.m. America/New_York.
- Works after Wi-Fi is disconnected.
- Touch next/previous controls work.
- Runs for 24 hours without a crash, memory growth, overheating, or undervoltage.
```

## Target repository structure

Ask Codex to create approximately this structure:

```text
love-frame/
├── AGENTS.md
├── LOVE_FRAME_PROJECT_GUIDE.md
├── README.md
├── requirements.txt
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── message_scheduler.py
│   ├── photo_loader.py
│   └── ui.py
├── assets/
│   ├── photos/
│   │   └── .gitkeep
│   └── fonts/
├── config/
│   └── config.example.json
├── data/
│   └── messages.example.json
├── scripts/
│   ├── install_pi.sh
│   ├── run_mac.sh
│   ├── run_pi.sh
│   └── deploy_to_pi.sh
├── system/
│   └── labwc-autostart.example
└── tests/
    ├── test_message_scheduler.py
    ├── test_photo_loader.py
    └── fixtures/
```

The `.gitignore` should exclude:

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
*.log
cache/
assets/photos/*
!assets/photos/.gitkeep
data/messages.local.json
config/config.local.json
.DS_Store
```

---

# 5. Build the software with Codex

Complete one phase at a time. Review the diff and run tests before moving on.

## Phase A — Scaffold and configuration

- [ ] Create the repository tree.
- [ ] Add `.gitignore` before adding personal content.
- [ ] Add sample configuration and sample messages.
- [ ] Add a clear `README.md`.
- [ ] Create a Python virtual environment on the Mac.
- [ ] Install development dependencies.
- [ ] Commit the scaffold.

Codex prompt:

```text
Implement Phase A only. Create the approved repository structure, privacy-safe .gitignore, example configuration, example messages, requirements, and README. Add no real photos or private messages. Run any available validation, summarize the files created, and stop for review.
```

Suggested local commands:

```bash
cd ~/Developer/love-frame
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pygame pillow pytest
```

## Phase B — Message scheduler

- [ ] Parse `America/New_York` correctly.
- [ ] Change the effective day at 8:00 a.m.
- [ ] Support explicitly dated messages.
- [ ] Rotate general messages when no dated message exists.
- [ ] Provide a harmless fallback if the file is missing/empty.
- [ ] Test 7:59 a.m., 8:00 a.m., DST dates, restart behavior, and invalid JSON.

Codex prompt:

```text
Implement Phase B only: the deterministic daily message scheduler and its tests. The effective date changes at 08:00 America/New_York. Prefer date-specific messages, otherwise rotate through local messages. It must work offline and after restarts. Run the tests and stop for review.
```

## Phase C — Photo loader

- [ ] Discover JPEG, JPG, PNG, and WEBP files.
- [ ] Ignore hidden and unsupported files.
- [ ] Shuffle without immediately repeating the current image.
- [ ] Auto-rotate based on EXIF orientation.
- [ ] Crop to fill 1024×600 without stretching.
- [ ] Keep only current/next images in memory.
- [ ] Skip corrupt images without crashing.
- [ ] Show a friendly placeholder if no photos exist.
- [ ] Test the loader with generated fixture images.

Codex prompt:

```text
Implement Phase C only: a low-memory photo discovery, EXIF orientation, crop-to-fill, shuffle, and caching pipeline for 1024x600. Never preload all full-resolution photos. Skip corrupt files and show a placeholder when the folder is empty. Add and run tests, then stop for review.
```

## Phase D — Full-screen interface

- [ ] Show a photo full-screen.
- [ ] Add a readable gradient/card for the daily message.
- [ ] Change photos every 10–20 seconds, configurable.
- [ ] Use a subtle fade transition.
- [ ] Tap left side for previous photo.
- [ ] Tap right side for next photo.
- [ ] Tap center to show/hide the message card.
- [ ] Support `Esc` or `Q` to exit during development.
- [ ] Run windowed on Mac and borderless fullscreen on the Pi.
- [ ] Hide the pointer after inactivity.
- [ ] Poll the message once per minute.
- [ ] Gracefully log errors rather than showing the desktop.

Codex prompt:

```text
Implement Phase D only: the Pygame UI for the approved architecture. Optimize for the Pi Zero 2 W and 1024x600 display. Add configurable slideshow timing, subtle fades, daily message card, touch/click zones, hidden cursor, Mac windowed mode, and Pi fullscreen mode. Run tests and a local smoke test, summarize performance considerations, and stop for review.
```

## Phase E — Installation and deployment scripts

- [ ] Create an idempotent Pi install script.
- [ ] Install only required Debian packages.
- [ ] Create production configuration from examples without overwriting private files.
- [ ] Add a `labwc` autostart entry.
- [ ] Add start/stop/log instructions.
- [ ] Create an `rsync` deployment script from Mac to Pi.
- [ ] Do not copy `.venv`, Git history, caches, or test photos to production.
- [ ] Document rollback.

Codex prompt:

```text
Implement Phase E only. Create safe, idempotent install and deployment scripts for Raspberry Pi OS Desktop with labwc. The app must autostart after desktop login. Do not overwrite personal photos, private messages, or local config during redeployment. Add dry-run guidance, rollback steps, and validation commands. Review all shell scripts for destructive behavior and stop for review.
```

## Phase F — Final local review

- [ ] Run all tests.
- [ ] Run formatter/linter selected by Codex.
- [ ] Run the app on the Mac in windowed 1024×600 mode.
- [ ] Test empty photo folder.
- [ ] Test invalid image.
- [ ] Test invalid message file.
- [ ] Test 7:59 and 8:00 simulated times.
- [ ] Check that private content is not staged by Git.
- [ ] Commit the working Mac version.

Codex prompt:

```text
Perform Phase F as a release-readiness review. Run the full test suite and static checks, inspect the git diff, verify ignored private content cannot be committed accidentally, and identify any Pi Zero 2 W memory or startup risks. Fix only clearly safe issues, rerun validation, and give me a go/no-go report.
```

---

# 6. Prepare the microSD card

Follow the official [Raspberry Pi getting-started documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Flash Raspberry Pi OS

- [ ] Install Raspberry Pi Imager on your Mac.
- [ ] Insert the 128 GB microSD using its SD adapter or card reader.
- [ ] Select **Raspberry Pi Zero 2 W** as the device.
- [ ] Select **Raspberry Pi OS (64-bit) with Desktop**, not Lite.
- [ ] Select the Samsung 128 GB card carefully.
- [ ] Open OS customization.

Use these recommended settings:

| Setting | Value |
|---|---|
| Hostname | `loveframe` |
| Username | `vic` |
| Password | A unique password stored safely |
| Wi-Fi | Your **2.4 GHz** network name and password |
| Wireless country | US |
| Time zone | `America/New_York` |
| Keyboard | US |
| SSH | Enabled; password authentication is acceptable for initial setup |

The Zero 2 W supports 2.4 GHz Wi-Fi, not 5 GHz-only networks.

- [ ] Write the image.
- [ ] Allow Imager to verify it.
- [ ] Eject the card safely.
- [ ] Insert it into the Pi.

## First boot

- [ ] Place the Pi in its existing case.
- [ ] Connect HDMI from Pi to Eyoyo.
- [ ] Connect the MakerSpot hub to the Pi port labeled **USB**.
- [ ] Connect the Eyoyo touch cable to the hub.
- [ ] Connect power to **PWR IN** last.
- [ ] Wait up to two minutes for the first boot.
- [ ] Confirm the desktop appears at 1024×600.
- [ ] Touch the screen and confirm the pointer responds.

Do not seal electronics inside the custom enclosure yet.

---

# 7. Configure Raspberry Pi OS

## Connect from the Mac

```bash
ssh vic@loveframe.local
```

Type `yes` the first time, then enter the password created in Imager.

## Update the Pi

```bash
sudo apt update
sudo apt -y full-upgrade
sudo reboot
```

Reconnect after the reboot.

## Verify date and time

```bash
timedatectl
```

Confirm:

- Time zone is `America/New_York`.
- System clock synchronized is `yes`.
- Local time is correct.

If not:

```bash
sudo timedatectl set-timezone America/New_York
```

## Enable desktop auto-login and disable blanking

Open the Pi's **Preferences → Control Centre**:

- [ ] System → Desktop Auto Login: enabled.
- [ ] Display → Screen Blanking: disabled.
- [ ] Interfaces → SSH: enabled.
- [ ] Reboot after changing these settings.

The same blanking setting is available through:

```bash
sudo raspi-config
```

Then select `Display Options → Screen Blanking` and disable it.

## Install runtime dependencies

Let the approved `scripts/install_pi.sh` perform this if Codex created it. The underlying packages should be close to:

```bash
sudo apt install -y python3-pygame python3-pil python3-pil.imagetk rsync git
```

Avoid installing Chromium, Docker, Node, or a large desktop framework for this project.

---

# 8. Deploy the app to the Pi

## Preferred: use the reviewed deployment script

From the Mac:

```bash
cd ~/Developer/love-frame
./scripts/deploy_to_pi.sh vic@loveframe.local
```

## Manual fallback

```bash
rsync -av --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'assets/photos/' \
  --exclude 'data/messages.local.json' \
  --exclude 'config/config.local.json' \
  ~/Developer/love-frame/ \
  vic@loveframe.local:/home/vic/love-frame/
```

Be careful with `--delete`: it must target only `/home/vic/love-frame/`, never your home directory or the SD-card root.

## Copy private photos and messages separately

```bash
rsync -av ~/Developer/love-frame/assets/photos/ \
  vic@loveframe.local:/home/vic/love-frame/assets/photos/

scp ~/Developer/love-frame/data/messages.local.json \
  vic@loveframe.local:/home/vic/love-frame/data/messages.local.json

scp ~/Developer/love-frame/config/config.local.json \
  vic@loveframe.local:/home/vic/love-frame/config/config.local.json
```

## First manual run on the Pi

SSH into the Pi, then run:

```bash
cd /home/vic/love-frame
python3 -m app.main --fullscreen
```

Check:

- [ ] Fullscreen is exactly 1024×600.
- [ ] Photos fill the display without stretching.
- [ ] Portrait photos crop intelligently.
- [ ] Message is readable from several feet away.
- [ ] Left/right/center touch zones work.
- [ ] Transitions are smooth.
- [ ] There is no desktop panel visible.
- [ ] App exits cleanly with a keyboard during testing.

---

# 9. Configure automatic startup

Raspberry Pi OS uses `labwc` for desktop autostart. Raspberry Pi's official kiosk tutorial uses this file:

```text
~/.config/labwc/autostart
```

The reviewed installer should add a line similar to:

```bash
/home/vic/love-frame/scripts/run_pi.sh >> /home/vic/love-frame/loveframe.log 2>&1 &
```

Do not repeatedly append duplicate lines. The installation script should check first.

Then reboot:

```bash
sudo reboot
```

Acceptance check:

- [ ] Pi boots without a keyboard or mouse.
- [ ] Desktop logs in automatically.
- [ ] LoveFrame opens full-screen automatically.
- [ ] Slideshow starts without clicking anything.
- [ ] Reboot a second time to prove startup is consistent.

---

# 10. Test reliability before building the enclosure

## Power and temperature

SSH into the Pi and run:

```bash
vcgencmd get_throttled
vcgencmd measure_temp
free -h
```

Expected:

- `get_throttled=0x0` after normal operation.
- No lightning-bolt/low-voltage warning.
- No random restart or touch disconnect.
- Temperature remains comfortably below the thermal-throttling range.
- Free memory stabilizes instead of shrinking continuously.

## 24-hour test

- [ ] Leave it running for at least 24 hours outside the final enclosure.
- [ ] Confirm several complete photo rotations.
- [ ] Confirm the message changes within one minute after 8:00 a.m.
- [ ] Disconnect Wi-Fi temporarily and confirm slideshow/message still work.
- [ ] Reconnect Wi-Fi.
- [ ] Reboot and confirm the same day's message returns.
- [ ] Inspect `loveframe.log` for repeated errors.

## If it is unstable

1. Confirm the official/quality 5V supply is being used.
2. Remove unnecessary USB devices.
3. Test the screen and touch cable again.
4. Check `vcgencmd get_throttled`.
5. Reduce fade duration or cache size if animation stutters.
6. Only then consider a powered USB hub or separate supported screen power arrangement.

Do not disable USB current protections to hide a power problem.

---

# 11. Design the Alexa-style enclosure

Do this only after the electronics pass the 24-hour test.

## Design requirements

- [ ] Matte black Echo Show-style wedge.
- [ ] Screen angled approximately 20–30° back from vertical.
- [ ] Front bezel does not cover the visible screen or touch area.
- [ ] Internal mount for Pi Zero case or bare Pi on standoffs.
- [ ] Internal mount/retainer for the OTG hub.
- [ ] Short, smooth cable routes without tight bends.
- [ ] Rear or bottom exit for the power cable.
- [ ] Ventilation slots near Pi/heatsinks.
- [ ] Removable rear panel for microSD and servicing.
- [ ] Rubber feet.
- [ ] No adhesive on the bare PCB.
- [ ] No pressure on the LCD glass.

Amazon lists the Eyoyo at approximately 6.4 × 4 × 0.6 inches, but measure the actual unit before CAD work. Product listings are not precise enough for a fitted enclosure.

## Measurements to record in millimeters

- [ ] Overall screen width, height, and thickness.
- [ ] Visible display opening.
- [ ] Corner radius.
- [ ] HDMI and USB port positions.
- [ ] Button/headphone positions that must remain accessible.
- [ ] Mounting-hole spacing and screw size.
- [ ] Pi case dimensions.
- [ ] OTG hub dimensions.
- [ ] Cable connector clearance.

## CAD/print specification

- Material: black PETG or PLA+.
- Wall thickness: approximately 2.4–3.0 mm.
- Use heat-set inserts or M2.5 screws only if the design requires them.
- Print the front bezel first as a cheap fit test.
- Print the entire enclosure only after the bezel and ports fit.

Use this [Echo Show-inspired Raspberry Show model](https://www.printables.com/model/1006894-raspberry-show-a-raspberry-pi-3b4-case-with-embedd) as a visual reference only. It is for different hardware and must not be printed unchanged.

## Enclosure workflow

- [ ] Photograph the front, rear, and every port with a ruler visible.
- [ ] Record all measurements.
- [ ] Create or adapt the CAD model.
- [ ] Print a thin front-bezel test.
- [ ] Correct fit and port alignment.
- [ ] Print final body and rear panel at FIU.
- [ ] Dry-fit electronics with power disconnected.
- [ ] Add rubber feet and cable retainers.
- [ ] Power on with the rear panel open.
- [ ] Confirm touch, Wi-Fi, temperature, and cable strain.
- [ ] Close the enclosure.
- [ ] Repeat a four-hour thermal test.

---

# 12. Everyday updates

## Add photos

On the Mac, add photos to:

```text
~/Developer/love-frame/assets/photos/
```

Then run:

```bash
rsync -av ~/Developer/love-frame/assets/photos/ \
  vic@loveframe.local:/home/vic/love-frame/assets/photos/
```

The application should periodically rescan the directory or be restarted after an update.

## Update messages

Edit:

```text
~/Developer/love-frame/data/messages.local.json
```

Validate it:

```bash
python3 -m json.tool ~/Developer/love-frame/data/messages.local.json >/dev/null
```

Copy it:

```bash
scp ~/Developer/love-frame/data/messages.local.json \
  vic@loveframe.local:/home/vic/love-frame/data/messages.local.json
```

## Restart the app

The finished repository should document its exact restart method. During early testing, rebooting is acceptable:

```bash
ssh vic@loveframe.local sudo reboot
```

## Safe shutdown

Never routinely pull the power while the Pi is running. Shut it down first:

```bash
ssh vic@loveframe.local sudo poweroff
```

Wait until activity stops before unplugging it.

---

# 13. Final definition of done

## Hardware

- [ ] Correct HDMI/USB touchscreen installed.
- [ ] Stable official/quality power supply.
- [ ] HDMI and touch work after repeated restarts.
- [ ] No undervoltage or random restarts.
- [ ] Pi and hub are securely mounted.
- [ ] Ventilation is unobstructed.
- [ ] Finished wedge enclosure resembles an Echo Show.

## Software

- [ ] App starts automatically after a cold boot.
- [ ] Fullscreen resolution is 1024×600.
- [ ] Photos do not stretch.
- [ ] Corrupt/missing photos do not crash the app.
- [ ] Daily message changes within one minute after 8:00 a.m.
- [ ] Date-specific messages override rotating messages.
- [ ] App works without internet.
- [ ] Touch navigation works.
- [ ] Cursor and desktop chrome stay hidden.
- [ ] Private photos/messages are excluded from Git.
- [ ] Tests pass.
- [ ] 24-hour reliability test passes.

## Gift/presentation

- [ ] At least 30 good photos loaded.
- [ ] At least 30 lovely messages loaded.
- [ ] Important dates verified.
- [ ] Screen brightness is comfortable.
- [ ] Cables are hidden and strain-relieved.
- [ ] Final exterior is clean.
- [ ] Backup copy of code, photos, messages, and configuration exists on the Mac.

---

# 14. Recommended implementation order

1. [ ] Buy the Eyoyo screen and confirm the power supply.
2. [ ] Create the Codex project folder and move this guide into it.
3. [ ] Use the first Codex planning prompt.
4. [ ] Create and review `AGENTS.md`.
5. [ ] Complete software Phases A–F on the Mac.
6. [ ] Flash and configure Raspberry Pi OS.
7. [ ] Test screen, HDMI, touch, Wi-Fi, and power.
8. [ ] Deploy the app to the Pi.
9. [ ] Configure automatic startup.
10. [ ] Complete the 24-hour reliability test.
11. [ ] Measure the final hardware.
12. [ ] Design and 3D-print the Echo Show-style enclosure at FIU.
13. [ ] Assemble and repeat thermal/restart tests.
14. [ ] Load the final private photos and messages.
15. [ ] Back everything up and present the finished LoveFrame.

---

# Reference links

- [Raspberry Pi Zero 2 W specifications](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)
- [Raspberry Pi getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html)
- [Raspberry Pi configuration](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [Raspberry Pi remote access/SSH](https://www.raspberrypi.com/documentation/remote-access/)
- [Raspberry Pi kiosk/autostart tutorial](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/)
- [Official OpenAI Codex quickstart](https://learn.chatgpt.com/docs/quickstart)
- [Official OpenAI `AGENTS.md` guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Official OpenAI Codex best practices](https://learn.chatgpt.com/guides/best-practices)

Prices and stock can change. Verify the listing and local availability before purchasing.
