msi-perkeyrgb
==================

This program allows you to control SteelSeries per-key RGB backlighting on MSI laptops — both the **keyboard** and the **lightbar / dragon logo**.

It works with devices that expose two SteelSeries HID interfaces:

| Interface | USB ID | Controls |
| --------- | ------ | -------- |
| KLC (Keyboard Light Control) | `1038:1122` | Per-key keyboard backlight |
| ALC (Ambient Light Control)  | `1038:1161` | Lightbar and dragon logo |

This is an unofficial tool. I am not affiliated with MSI nor SteelSeries in any way.

> **Fork note:** this version extends the [original msi-perkeyrgb](https://github.com/Askannz/msi-perkeyrgb) with lightbar / logo (ALC device) support and `--kbd` / `--bar` target flags.


Installation
----------

### Ubuntu / Debian

```bash
sudo apt install git python3-venv libhidapi-hidraw0

git clone https://github.com/Askannz/msi-perkeyrgb
cd msi-perkeyrgb/
python3 -m venv .venv
source .venv/bin/activate
pip install .

sudo cp 99-msi-rgb.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Arch Linux

AUR package: [msi-perkeyrgb](https://aur.archlinux.org/packages/msi-perkeyrgb/) (may lag behind Git)

After installation, **reboot** or at least re-login so the udev rule and group membership take effect.


Permissions
----------

The included udev rule (`99-msi-rgb.rules`) grants read/write access to both KLC and ALC HID interfaces for the `plugdev` group. Make sure your user is in that group:

```bash
sudo usermod -aG plugdev $USER
```

Then reboot (or `newgrp plugdev`). Verify:

```bash
groups            # should list plugdev
ls -l /dev/hidraw*  # KLC and ALC devices should show group "plugdev"
```

If you still get permission errors, find the correct `/dev/hidraw*` nodes and `chmod 666` them as a quick workaround.


Usage
----------

### Steady color — whole system

```bash
msi-perkeyrgb -s ff0000          # everything red
msi-perkeyrgb -s ffffff          # everything white
msi-perkeyrgb -d                 # disable all lighting
```

### Target selection

Use `--kbd` or `--bar` to control keyboard and lightbar independently:

```bash
msi-perkeyrgb --kbd -s ffffff    # white keyboard only
msi-perkeyrgb --bar -s ff00ff   # magenta lightbar only
msi-perkeyrgb --bar -d          # disable lightbar only
msi-perkeyrgb --kbd -d          # disable keyboard only
```

When neither flag is given, both devices are targeted.

### Per-key configuration (keyboard only)

```bash
msi-perkeyrgb --model <MODEL> -c <config-file>
```

See the [configuration file guide](https://github.com/Askannz/msi-perkeyrgb/wiki/Configuration-file-guide) for syntax and examples.

### Presets (keyboard only)

```bash
msi-perkeyrgb --model <MODEL> --list-presets
msi-perkeyrgb --model <MODEL> -p <preset>
```

### Other flags

| Flag | Description |
| ---- | ----------- |
| `-v`, `--version` | Print version and exit |
| `--list-models` | List supported laptop models |
| `--id VENDOR:PRODUCT` | Override USB ID (advanced) |


Desktop shortcuts
----------

You can create `.desktop` files to toggle lighting from your app launcher. Example (`~/.local/share/applications/keycolor-off.desktop`):

```ini
[Desktop Entry]
Type=Application
Name=RGB Off
Icon=keyboard-brightness
Exec=bash -lc 'cd "$HOME/.local/src/msi-perkeyrgb" && source ".venv/bin/activate" && msi-perkeyrgb -d'
Terminal=false
```


Compatibility
----------

Tested on:

| Model | Keyboard (KLC) | Lightbar/Logo (ALC) |
| ----- | --------------- | ------------------- |
| MSI Raider 18 HX (A2XWIG) | ✓ | ✓ |
| GE63 | ✓ | — |
| GE73 | ✓ | — |
| GE75 | ✓ | — |
| GL63 | ✓ | — |
| GS63 | ✓ | — |
| GS65 | ✓ | — |
| GS75 | ✓ | — |
| GT63 | ✓ | — |
| GT75 | ✓ | — |

If you have test results for other models — especially ALC support — please open an issue.


Requirements
----------

* Python 3.4+
* libhidapi 0.8+
  * **Ubuntu**: `sudo apt install libhidapi-hidraw0`
  * **Arch**: `sudo pacman -S hidapi`
  * **Fedora**: `sudo dnf install hidapi`


How it works
----------

MSI laptops with SteelSeries RGB expose two USB HID interfaces:

* **KLC** (`1038:1122`) — keyboard per-key RGB. The original msi-perkeyrgb sends color packets via feature reports split into four regions (alphanum, enter, modifiers, numpad), each carrying up to 42 key entries of 12 bytes.

* **ALC** (`1038:1161`) — lightbar and logo. Uses the same packet format as KLC with one critical difference: key entries use sequential indices `0..41` instead of real keycodes. This was discovered by brute-force probing and Wireshark analysis.

Both interfaces share the same protocol:
1. Send feature reports (`0x0e`) for each of the four regions
2. Send a refresh command (output report `0x09` + 63 zero bytes)

The original HID protocol was reverse-engineered by capturing USB traffic from SteelSeries Engine on Windows. Detailed protocol documentation by [TauAkiou](https://github.com/TauAkiou) is available [here](documentation/0b_packet_information/msi-kb-effectdoc).


Credits
----------

* [Askannz](https://github.com/Askannz) — original msi-perkeyrgb
* [TauAkiou](https://github.com/TauAkiou) — protocol reverse-engineering and effects documentation
* [tbh1](https://github.com/tbh1) — preset effect packet dumps
* ALC (lightbar/logo) support — reverse-engineered on MSI Raider 18 HX under Linux

The HID communication code was inspired by [MSIKLM](https://github.com/Gibtnix/MSIKLM).
