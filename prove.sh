#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
# to run individual tests: ./prove.sh tests.test_foo tests.test_bar
python3 -m unittest -v "$@"
