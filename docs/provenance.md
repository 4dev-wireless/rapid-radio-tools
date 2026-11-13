# Source provenance and scope

The public repository was assembled from a local Rapid Radio investigation.

| Public file | Original material |
| --- | --- |
| `tools/asr_at_tui.py` | Original standalone ASR USB modem TUI; code retained unchanged |
| `docs/at-tui.md` | Original TUI usage notes, updated for this repository's paths and virtual environment |
| `tools/arom_descriptor_probe.py` | Original descriptor probe, with help output and dependency/access error handling added |
| `tools/catch_bootloader.sh` | Original helper; comments clarified and trailing whitespace removed |
| `configs/arom-readonly-probe/download.json` | Metadata-only recipe extracted from the local AROM probe archive |
| `docs/reference/usb-runtime-descriptors.txt` | Runtime descriptor capture with the serial number and host bus/device numbers removed |

The firmware dumps, NVM/factory partitions, vendor Aboot distributions,
drivers, loader images, baseline archive, packet captures, executable string
output, and hardware photos remain outside the public repository. They have
not been reviewed or licensed for redistribution here.

The original workspace also contained an unmodified checkout of
[linux-msm/qdl](https://github.com/linux-msm/qdl) at commit
`657f12fa64582407fcca5144151a5879e7cd59a6`. QDL is a separate project for
Qualcomm devices using Sahara/Firehose; its presence in the workspace does not
establish compatibility with this radio's ASR interfaces. It is not vendored
or included as a submodule.

The ASR identifiers and endpoint assignments in this repository come from the
local scripts and captured descriptors. They do not establish a particular
chip model, support for every Rapid Radio model, or a working flash procedure.
