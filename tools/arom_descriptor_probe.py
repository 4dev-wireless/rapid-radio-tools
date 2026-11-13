#!/usr/bin/env python3
"""Read-only USB descriptor probe for ASR AROM 2ecc:3004.

This script performs no interface claim, no kernel-driver detach, no endpoint
writes, no vendor requests, no RAM upload, and no flash operations. It only
reads standard USB descriptors and string descriptors already exposed by the
device during enumeration.
"""
import argparse
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    usb = None

VID = 0x2ECC
PID = 0x3004

def get_string(dev, idx):
    if not idx:
        return ""
    try:
        return usb.util.get_string(dev, idx) or ""
    except Exception as e:
        return f"<unreadable: {e}>"

def probe():
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("ASR AROM device 2ecc:3004 not found.", file=sys.stderr)
        print("Check with: lsusb -d 2ecc:3004", file=sys.stderr)
        return 2

    print(f"VID:PID       {dev.idVendor:04x}:{dev.idProduct:04x}")
    print(f"bcdUSB        0x{dev.bcdUSB:04x}")
    print(f"bcdDevice     0x{dev.bcdDevice:04x}")
    print(f"Device class  0x{dev.bDeviceClass:02x}")
    print(f"Manufacturer  {get_string(dev, dev.iManufacturer)}")
    print(f"Product       {get_string(dev, dev.iProduct)}")
    print(f"Serial        {get_string(dev, dev.iSerialNumber)}")
    print()

    for cfg in dev:
        print(f"Configuration {cfg.bConfigurationValue}: interfaces={cfg.bNumInterfaces}, "
              f"maxPower={cfg.bMaxPower * 2}mA, attributes=0x{cfg.bmAttributes:02x}")
        for intf in cfg:
            print(f"  Interface {intf.bInterfaceNumber} alt={intf.bAlternateSetting} "
                  f"class=0x{intf.bInterfaceClass:02x} "
                  f"subclass=0x{intf.bInterfaceSubClass:02x} "
                  f"protocol=0x{intf.bInterfaceProtocol:02x} "
                  f"name={get_string(dev, intf.iInterface)!r}")
            for ep in intf:
                direction = "IN" if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN else "OUT"
                etype = usb.util.endpoint_type(ep.bmAttributes)
                print(f"    EP 0x{ep.bEndpointAddress:02x} {direction} "
                      f"type={etype} maxpacket={ep.wMaxPacketSize}")

    print("\nNo interface was claimed and no data was written to the device.")
    return 0

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if usb is None:
        print("PyUSB is not installed; install requirements.txt first.", file=sys.stderr)
        return 1
    try:
        return probe()
    except (usb.core.USBError, usb.core.NoBackendError) as exc:
        print(f"USB probe failed: {exc}", file=sys.stderr)
        print("Check USB permissions and that a libusb backend is installed.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
