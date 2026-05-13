#! /bin/bash

for ver in 3.11 3.12 3.13 3.14; do
    uv run --python $ver pytest
done
