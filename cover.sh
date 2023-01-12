#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
coverage run --branch -m unittest "$@"
if coverage report --skip-covered --show-missing --fail-under=100
then
	coverage erase
	git clean -xf htmlcov
else
	coverage html
fi
