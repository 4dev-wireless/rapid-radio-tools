PYTHON ?= python3

.PHONY: check
check:
	$(PYTHON) -m py_compile tools/asr_at_tui.py tools/arom_descriptor_probe.py
	$(PYTHON) tools/asr_at_tui.py --help
	$(PYTHON) tools/arom_descriptor_probe.py --help
	bash -n tools/catch_bootloader.sh
	$(PYTHON) -m json.tool configs/arom-readonly-probe/download.json > /dev/null
