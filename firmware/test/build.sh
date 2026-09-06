#!/bin/sh
# Slice the detector out of the shipping header and build the host test around it.
set -e
SRC=../src/acoustic_core.h
awk '/^\/\/ =+ onset detection/,/^\/\/ =+ bring-up/' "$SRC" \
  | sed '$d' > frag_new.h
c++ -O2 -std=c++17 -DNEWVER -DFRAGFILE='"frag_new.h"' -o det_new onset_regression.cpp
echo "built ./det_new from $SRC"
