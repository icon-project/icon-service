SHELL := /bin/bash

.PHONY: help
help:
	@awk '/^##/{c=substr($$0,3);next}c&&/^[[:alpha:]][-_[:alnum:]]+:/{print substr($$1,1,index($$1,":")),c}1{c=0}'\
	 $(MAKEFILE_LIST) | column -s: -t

## Run pytest
test:
	@python3 -m pytest -ra tests/ || exit -1

## Clean all - clean-build
clean: clean-build

clean-build:
	@$(RM) -r build/ dist/
	@$(RM) -r .eggs/ eggs/ *.egg-info/

## Build python wheel
build: clean-build
	@if [ "$$(python -c 'import sys; print(sys.version_info[0])')" != 3 ]; then \
		@echo "The script should be run on python3."; \
		exit -1; \
	fi

	@if ! python -c 'import wheel' &> /dev/null; then \
		pip install wheel; \
	fi

	python3 setup.py bdist_wheel
