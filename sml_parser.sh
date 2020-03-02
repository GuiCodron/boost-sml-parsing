#!/bin/bash

export LD_LIBRARY_PATH=$(llvm-config-6.0 --libdir)

python3 "$(dirname "$(readlink -f "$0")")"/sml_parser.py "$@"
