# Contributing

Keep changes focused and run `make check` before opening a pull request.
Describe the device, firmware revision, and USB mode used for any hardware
verification. Distinguish observed behavior from assumptions.

Do not add firmware dumps, vendor binaries, private keys, SIM identifiers,
account details, or raw device logs. Review command output and images for device
identifiers before sharing them. The `.gitignore` rules reduce accidental
inclusion but do not replace reviewing the files in a commit.

Changes that send new commands or alter USB transfers should explain exactly
what is sent and when. Keep the descriptor probe limited to standard descriptor
reads and the AT terminal free of automatic startup commands.

The local checks do not exercise USB communication. Report hardware testing
separately, and use mocks for automated transport checks so CI can run without
a connected device.
