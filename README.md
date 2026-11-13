# Rapid Radio Tools

USB inspection and AT-command tools collected while investigating a Rapid
Radio. The recorded device exposes ASR USB interfaces. These are research
utilities for the observed hardware; compatibility with other models or
firmware revisions has not been established.

## Tools

| Tool | Purpose | Device interaction |
| --- | --- | --- |
| [`arom_descriptor_probe.py`](tools/arom_descriptor_probe.py) | Inspect the `2ecc:3004` AROM device | Standard USB descriptor reads; no interface claim or upload |
| [`asr_at_tui.py`](tools/asr_at_tui.py) | Interactive AT-command terminal for `2ecc:3010` | Claims interface 2 and sends commands when you press Enter |
| [`catch_bootloader.sh`](tools/catch_bootloader.sh) | Experimental attempt to interrupt startup over `/dev/ttyACM0` | Immediately sends Ctrl-C, `version`, and `help` when the port appears |

The AT terminal accepts arbitrary commands, including commands that can reboot
or update a radio. The bootloader helper actively writes to the serial port.
Only the descriptor probe is intended for passive inspection. No flash or
recovery workflow is provided here.

## Setup

Use Linux with Python 3.10 or newer, a terminal with curses support, and a libusb
backend. On Debian/Ubuntu:

```bash
sudo apt install python3-venv libusb-1.0-0 usbutils
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the following commands from the repository root. They use the virtual
environment's Python explicitly, including when elevated USB access is needed.

```bash
# Inspect the device in AROM mode; this does not switch the radio into AROM.
lsusb -d 2ecc:3004
sudo .venv/bin/python tools/arom_descriptor_probe.py

# Open the AT terminal when the runtime USB device is present.
lsusb -d 2ecc:3010
sudo .venv/bin/python tools/asr_at_tui.py
```

The AT terminal sends no command on startup. Type a command and press Enter;
use Ctrl-C or Ctrl-D to exit. See the [AT terminal guide](docs/at-tui.md) for
controls, USB overrides, and troubleshooting. Review the
[bootloader helper notes](docs/bootloader.md) before running that script.

## Recorded USB interfaces

The runtime device `2ecc:3010` exposed these interfaces in the captured
descriptors:

| Interface | Function | Bulk IN | Bulk OUT |
| --- | --- | --- | --- |
| 2 | Mobile AT Interface | `0x81` | `0x0a` |
| 4 | Mobile Diag Interface | `0x82` | `0x0b` |

The diagnostic interface is recorded for reference; there is no diagnostic
client in this repository. The [descriptor capture](docs/reference/usb-runtime-descriptors.txt)
has its USB serial number and host bus/device numbers removed. The descriptor
probe prints the connected device's serial number, so review its output before
sharing it.

## Repository contents

```text
tools/                      Standalone Python and Bash utilities
configs/arom-readonly-probe/ Metadata-only AROM probe recipe
docs/                       Usage, limitations, and source provenance
.github/workflows/          Checks that do not require a connected radio
requirements.txt            Python USB dependency
```

The [AROM recipe](configs/arom-readonly-probe/README.md) contains only product
and protocol requirements. It does not include a loader or vendor executable.

## Development

```bash
make check
```

This checks Python syntax, both Python help commands, Bash syntax, and the JSON
recipe. It does not connect to USB devices or establish hardware compatibility.
GitHub Actions runs the same checks on Python 3.10 and 3.14.

For contributions, follow [CONTRIBUTING.md](CONTRIBUTING.md).


## License

These tools are free to use, modify, and redistribute for noncommercial purposes
under the accompanying license.

Commercial use requires a separate written agreement with the copyright holder
before use begins. This includes use in paid services, internal business
operations, and commercial products, whether or not the tools themselves are
sold.

The accompanying license file has not yet been added. No redistribution rights
for excluded vendor software or firmware are implied by this repository.
