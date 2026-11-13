# Metadata-only AROM probe recipe

`download.json` was extracted from the local
`ASR1601_AROM_READONLY_PROBE.zip` archive. It contains two `require` steps:

- Product: `arom|arom-tiny`
- Protocol version: `0.5`

There are no `call`, `partition`, `upload`, or flash steps and no loader images
in this directory. The archive name is historical; it does not confirm the
radio's chip model.

This recipe is retained as a reference for vendor tooling. Its behavior with a
vendor executable has not been validated as part of preparing this repository.
For standard USB descriptor inspection, use
`tools/arom_descriptor_probe.py` from the repository root.
