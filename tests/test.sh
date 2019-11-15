#/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f $0)")

cd $SCRIPT_DIR/..
python3 cpp-parse.py compile_commands.json tests/sm.cpp ""
