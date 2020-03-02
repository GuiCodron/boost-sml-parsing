#!/bin/bash

SCRIPT_DIR=$(readlink -f "$0")

sudo apt-get install llvm-6.0 libclang1-6.0

llvm_dir=$(llvm-config-6.0 --libdir)

if ! [ -e "$llvm_dir"/libclang.so ]; then
  if sudo ln -s "$llvm_dir"/libclang-6.0.so.1 "$llvm_dir"/libclang.so; then
    echo "Failed to install libclang.so"
    exit 1
  fi
fi

pip3 install --user -r "$SCRIPT_DIR"/requirements.txt
