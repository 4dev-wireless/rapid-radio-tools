#!/bin/bash
# Experimental: run with sudo bash tools/catch_bootloader.sh.
# Sends bytes to /dev/ttyACM0 as soon as it appears; see docs/bootloader.md.

echo "Waiting for bootloader..."

while true; do
    if [ -e /dev/ttyACM0 ]; then
        echo "BOOTLOADER CAPTURED!"

        # Send a Ctrl-C byte immediately (not a serial BREAK signal).
        echo -e "\x03" > /dev/ttyACM0 2>/dev/null
        echo -e "version\r\n" > /dev/ttyACM0 2>/dev/null
        echo -e "help\r\n" > /dev/ttyACM0 2>/dev/null

        # Try to read any response
        timeout 0.5 cat /dev/ttyACM0 2>/dev/null

        echo ""
        echo "Bootloader commands sent. Check if it stayed:"
        ls -la /dev/ttyACM* 2>/dev/null
        break
    fi
done
