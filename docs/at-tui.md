# ASR AT command TUI

`asr_at_tui.py` is a small curses terminal UI for the ASR runtime USB device
identified during the radio investigation:

- USB device: `2ecc:3010`
- interface: `2`
- bulk OUT: `0x0a`
- bulk IN: `0x81`

It sends nothing when it starts. Type an AT command and press Enter. The
transport drains stale input before each command and waits for a terminal
response followed by a quiet period, which avoids the one-command-lag problem
from delayed modem output.

## Install and run

From the repository root, install the dependencies as described in the
[setup guide](../README.md#setup), then run:

```bash
sudo .venv/bin/python tools/asr_at_tui.py
```

If your device is not the default one, override the USB settings, for example:

```bash
sudo .venv/bin/python tools/asr_at_tui.py --pid 0x3010 --interface 2 --ep-in 0x81 --ep-out 0x0a
```

The program claims the AT interface while it is open and attempts to reattach
the kernel driver when it exits. Running as root is the simplest option until a
udev rule grants access to your user.

If ModemManager interferes with the interface, temporarily stop it with
`sudo systemctl stop ModemManager` and restore it after closing the TUI with
`sudo systemctl start ModemManager`. This temporarily affects other modems
managed by that service.

## Controls

- Type a command and press Enter: send it with `CR` line termination.
- Up/Down: command history.
- PgUp/PgDn: scroll transcript.
- Mouse wheel: scroll transcript without changing the command line.
- `Ctrl-L` or `F2`: clear transcript.
- `:help`, `:clear`, `:reconnect`, `:quit`: local UI commands.
- `Ctrl-C` / `Ctrl-D`: exit without sending a command.

The TUI does not prevent commands that can reboot or update the radio. Treat
commands such as `AT$MYDOWNLOAD=1` and `AT$MYFOTA=...` as destructive operations
and send them only deliberately.
