#!/usr/bin/env python3
"""Small curses TUI for sending AT commands to an ASR USB modem.

The program does not send a command on startup.  It only claims the configured
USB interface and listens for unsolicited input until the user presses Enter.
"""

from __future__ import annotations

import argparse
import curses
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional


try:
    import usb.core
    import usb.util
except ImportError:  # pragma: no cover - exercised on machines without PyUSB
    usb = None


TERMINAL_RE = re.compile(
    rb"(?:^|\r?\n)(?:OK|ERROR|NO CARRIER|NO ANSWER|BUSY)\r?\n"
    rb"|(?:^|\r?\n)\+CME ERROR:\s*[^\r\n]+"
)


@dataclass
class UsbSettings:
    vid: int = 0x2ECC
    pid: int = 0x3010
    interface: int = 2
    ep_out: int = 0x0A
    ep_in: int = 0x81
    read_size: int = 4096
    command_timeout: float = 4.0
    quiet_after_terminal: float = 0.5


class AtTransport:
    """Direct bulk USB transport for the AT interface."""

    def __init__(self, settings: UsbSettings):
        self.settings = settings
        self.dev = None
        self.detached_kernel_driver = False

    @property
    def connected(self) -> bool:
        return self.dev is not None

    def open(self) -> None:
        if usb is None:
            raise RuntimeError("PyUSB is not installed; run: python3 -m pip install pyusb")

        dev = usb.core.find(idVendor=self.settings.vid, idProduct=self.settings.pid)
        if dev is None:
            raise RuntimeError(
                f"USB device {self.settings.vid:04x}:{self.settings.pid:04x} not found"
            )

        try:
            if dev.is_kernel_driver_active(self.settings.interface):
                dev.detach_kernel_driver(self.settings.interface)
                self.detached_kernel_driver = True
        except usb.core.USBError as exc:
            # Some backends do not implement kernel-driver queries.  Claiming
            # the interface below will provide the useful error in that case.
            if getattr(exc, "errno", None) not in (None, 95):
                raise

        try:
            usb.util.claim_interface(dev, self.settings.interface)
        except Exception:
            if self.detached_kernel_driver:
                try:
                    dev.attach_kernel_driver(self.settings.interface)
                except Exception:
                    pass
                self.detached_kernel_driver = False
            raise

        self.dev = dev

    def close(self) -> None:
        if self.dev is None:
            return

        dev = self.dev
        try:
            usb.util.release_interface(dev, self.settings.interface)
        finally:
            if self.detached_kernel_driver:
                try:
                    dev.attach_kernel_driver(self.settings.interface)
                except Exception:
                    pass
            self.dev = None
            self.detached_kernel_driver = False

    def _read(self, timeout_ms: int) -> bytes:
        if self.dev is None:
            raise RuntimeError("USB device is not connected")
        return bytes(
            self.dev.read(
                self.settings.ep_in,
                self.settings.read_size,
                timeout=timeout_ms,
            )
        )

    def drain(self, max_seconds: float = 0.35) -> int:
        """Discard bytes left by a previous command; return the byte count."""
        deadline = time.monotonic() + max_seconds
        discarded = 0
        while time.monotonic() < deadline:
            try:
                discarded += len(self._read(50))
            except usb.core.USBTimeoutError:
                break
        return discarded

    def poll(self) -> bytes:
        """Read one short, non-blocking-ish chunk for unsolicited data."""
        try:
            return self._read(1)
        except usb.core.USBTimeoutError:
            return b""

    def send(self, command: str) -> bytes:
        """Send one command and wait for its terminal response plus quiet time."""
        if self.dev is None:
            raise RuntimeError("USB device is not connected")

        self.drain()
        wire_command = command.rstrip("\r\n") + "\r"
        self.dev.write(self.settings.ep_out, wire_command.encode(), timeout=1000)

        response = bytearray()
        deadline = time.monotonic() + self.settings.command_timeout
        last_rx: Optional[float] = None
        terminal_seen = False

        while time.monotonic() < deadline:
            try:
                chunk = self._read(100)
            except usb.core.USBTimeoutError:
                chunk = b""

            if chunk:
                response.extend(chunk)
                last_rx = time.monotonic()
                if TERMINAL_RE.search(response):
                    terminal_seen = True

            if (
                terminal_seen
                and last_rx is not None
                and time.monotonic() - last_rx >= self.settings.quiet_after_terminal
            ):
                break

        return bytes(response)


def parse_int(value: str) -> int:
    return int(value, 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Curses AT-command TUI for an ASR USB modem")
    parser.add_argument("--vid", type=parse_int, default=0x2ECC, help="USB vendor ID (default: 0x2ecc)")
    parser.add_argument("--pid", type=parse_int, default=0x3010, help="USB product ID (default: 0x3010)")
    parser.add_argument("--interface", type=parse_int, default=2, help="USB interface number (default: 2)")
    parser.add_argument("--ep-in", type=parse_int, default=0x81, help="bulk IN endpoint (default: 0x81)")
    parser.add_argument("--ep-out", type=parse_int, default=0x0A, help="bulk OUT endpoint (default: 0x0a)")
    parser.add_argument("--timeout", type=float, default=4.0, help="maximum response wait in seconds")
    parser.add_argument("--quiet", type=float, default=0.5, help="quiet period after OK/ERROR in seconds")
    return parser


class Ui:
    def __init__(self, screen: "curses.window", transport: AtTransport):
        self.screen = screen
        self.transport = transport
        self.transcript: deque[str] = deque(maxlen=2000)
        self.history: list[str] = []
        self.history_index: Optional[int] = None
        self.input_text = ""
        self.cursor = 0
        self.scroll_offset = 0
        self.ignoring_escape = False
        self.status = "Opening USB interface..."
        self.running = True

    def add(self, text: str) -> None:
        text = text.replace("\x00", "�")
        lines = text.splitlines()
        if not lines:
            self.transcript.append("")
        else:
            self.transcript.extend(lines)
        self.scroll_offset = 0

    def add_block(self, prefix: str, data: bytes) -> None:
        decoded = data.decode(errors="replace")
        self.add(prefix + decoded if decoded else prefix)

    def set_input(self, value: str) -> None:
        self.input_text = value
        self.cursor = len(value)

    def history_move(self, direction: int) -> None:
        if not self.history:
            return
        if self.history_index is None:
            self.history_index = len(self.history)
        self.history_index = max(0, min(len(self.history), self.history_index + direction))
        self.set_input(self.history[self.history_index] if self.history_index < len(self.history) else "")

    def render(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 6 or width < 40:
            self.screen.addstr(0, 0, "Terminal too small; need at least 40x6")
            self.screen.refresh()
            return

        connected = "connected" if self.transport.connected else "disconnected"
        title = " ASR AT TUI "
        device = (
            f"{self.transport.settings.vid:04x}:{self.transport.settings.pid:04x} "
            f"if={self.transport.settings.interface} {connected}"
        )
        self.screen.addnstr(0, 0, title, width - 1, curses.A_REVERSE)
        self.screen.addnstr(0, max(0, width - len(device) - 1), device, width - 1, curses.A_REVERSE)

        body_height = height - 3
        lines = list(self.transcript)
        start = max(0, len(lines) - body_height - self.scroll_offset)
        visible = lines[start : start + body_height]
        for row, line in enumerate(visible, start=1):
            self.screen.addnstr(row, 0, line, width - 1)

        self.screen.hline(height - 2, 0, curses.ACS_HLINE, width)
        prompt = "> "
        available = width - len(prompt) - 1
        shown = self.input_text
        if len(shown) > available:
            left = max(0, self.cursor - available + 1)
            shown = shown[left : left + available]
            cursor_screen = len(prompt) + self.cursor - left
        else:
            cursor_screen = len(prompt) + self.cursor
        self.screen.addnstr(height - 1, 0, prompt + shown, width - 1)
        self.screen.addnstr(height - 2, 2, self.status, width - 3)
        self.screen.move(height - 1, min(width - 1, cursor_screen))
        self.screen.refresh()

    def handle_special(self, key: int) -> None:
        if key in (curses.KEY_UP,):
            self.history_move(-1)
        elif key in (curses.KEY_DOWN,):
            self.history_move(1)
        elif key == curses.KEY_LEFT:
            self.cursor = max(0, self.cursor - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor = min(len(self.input_text), self.cursor + 1)
        elif key in (curses.KEY_HOME, 1):
            self.cursor = 0
        elif key in (curses.KEY_END, 5):
            self.cursor = len(self.input_text)
        elif key in (curses.KEY_BACKSPACE, 8, 127):
            if self.cursor:
                self.input_text = self.input_text[: self.cursor - 1] + self.input_text[self.cursor :]
                self.cursor -= 1
        elif key == curses.KEY_DC:
            if self.cursor < len(self.input_text):
                self.input_text = self.input_text[: self.cursor] + self.input_text[self.cursor + 1 :]
        elif key == 21:  # Ctrl-U
            self.input_text = self.input_text[self.cursor :]
            self.cursor = 0
        elif key == 23:  # Ctrl-W
            before = self.input_text[: self.cursor].rstrip()
            before = before[: before.rfind(" ") + 1]
            self.input_text = before + self.input_text[self.cursor :]
            self.cursor = len(before)
        elif key == 12:  # Ctrl-L
            self.transcript.clear()
            self.status = "Transcript cleared"
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = min(len(self.transcript), self.scroll_offset + 10)
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = max(0, self.scroll_offset - 10)

    def handle_mouse(self) -> None:
        try:
            _, _, _, _, button_state = curses.getmouse()
        except curses.error:
            return

        wheel_up = getattr(curses, "BUTTON4_PRESSED", 0)
        wheel_down = getattr(curses, "BUTTON5_PRESSED", 0)
        if button_state & wheel_up:
            self.scroll_offset = min(len(self.transcript), self.scroll_offset + 3)
        elif button_state & wheel_down:
            self.scroll_offset = max(0, self.scroll_offset - 3)

    def submit(self) -> None:
        command = self.input_text.strip()
        self.set_input("")
        self.history_index = None
        if not command:
            return
        if command == ":quit":
            self.running = False
            return
        if command == ":clear":
            self.transcript.clear()
            return
        if command == ":reconnect":
            self.reconnect()
            return
        if command == ":help":
            self.add("Commands: type an AT command and press Enter; :clear; :reconnect; :quit")
            self.add("Keys: Up/Down history, PgUp/PgDn scroll, Ctrl-C quit, Ctrl-L clear")
            return

        if not self.history or self.history[-1] != command:
            self.history.append(command)
        self.add(f">>> {command}")
        self.status = f"Sending {command!r}..."
        self.render()
        try:
            response = self.transport.send(command)
            self.add_block("", response)
            self.status = "Ready"
        except Exception as exc:
            self.add(f"[transport error] {exc}")
            self.status = "Disconnected; use :reconnect after checking the device"

    def reconnect(self) -> None:
        self.transport.close()
        try:
            self.transport.open()
            self.status = "Connected; no command sent"
            self.add("[connected]")
        except Exception as exc:
            self.status = "Disconnected"
            self.add(f"[connect error] {exc}")

    def poll_unsolicited(self) -> None:
        if not self.transport.connected:
            return
        try:
            data = self.transport.poll()
        except Exception as exc:
            self.add(f"[receive error] {exc}")
            self.status = "Disconnected"
            return
        if data:
            self.add_block("[async] ", data)

    def run(self) -> None:
        try:
            curses.set_escdelay(25)
        except AttributeError:
            pass
        self.screen.nodelay(True)
        self.screen.keypad(True)
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
            curses.mouseinterval(0)
        except curses.error:
            pass
        self.reconnect()

        while self.running:
            self.poll_unsolicited()
            self.render()
            key = self.screen.getch()
            if key == -1:
                time.sleep(0.03)
                continue
            # If a terminal sends an escape sequence that curses does not
            # recognize, consume it instead of inserting its printable bytes
            # into the command line.
            if self.ignoring_escape:
                if 0x40 <= key <= 0x7E:
                    self.ignoring_escape = False
                continue
            if key == 27:
                self.ignoring_escape = True
                continue
            if key in (3, 4):  # Ctrl-C / Ctrl-D
                self.running = False
            elif key in (10, 13):
                self.submit()
            elif key == curses.KEY_F2:
                self.transcript.clear()
            elif key == curses.KEY_MOUSE:
                self.handle_mouse()
            elif key < 32 or key == 127 or key > 126:
                self.handle_special(key)
            else:
                self.input_text = self.input_text[: self.cursor] + chr(key) + self.input_text[self.cursor :]
                self.cursor += 1


def main() -> int:
    args = build_parser().parse_args()
    settings = UsbSettings(
        vid=args.vid,
        pid=args.pid,
        interface=args.interface,
        ep_in=args.ep_in,
        ep_out=args.ep_out,
        command_timeout=args.timeout,
        quiet_after_terminal=args.quiet,
    )
    transport = AtTransport(settings)
    try:
        def run_ui(screen: "curses.window") -> None:
            Ui(screen, transport).run()

        curses.wrapper(run_ui)
    except KeyboardInterrupt:
        pass
    finally:
        transport.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
