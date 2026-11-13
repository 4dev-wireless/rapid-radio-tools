# Experimental bootloader helper

`tools/catch_bootloader.sh` waits for `/dev/ttyACM0`, then writes a Ctrl-C byte,
`version`, and `help`, and attempts to read output for half a second. The Ctrl-C
byte is not a serial BREAK signal. A success message only means the port was
found; it does not establish that a bootloader was interrupted.

The script is retained from the investigation. It uses a busy polling loop,
does not configure baud rate or terminal settings, and does not distinguish
the radio from another device using `/dev/ttyACM0`. Its `echo` commands also
append newlines. It is not a confirmed recovery procedure.

Use it only when `/dev/ttyACM0` is known to belong to the intended device and
you deliberately want to send those bytes:

```bash
sudo bash tools/catch_bootloader.sh
```

It requires Bash, GNU `timeout`, `cat`, and `ls`. Ctrl-C stops the waiting loop.
Do not run it as part of automated discovery or CI.
