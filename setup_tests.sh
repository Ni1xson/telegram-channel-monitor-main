#!/bin/bash
# Simple helper to install dependencies required for running tests
set -e

if ! command -v python3 &> /dev/null; then
  echo "Python 3 is required" >&2
  exit 1
fi

pip3 install -r requirements.txt

echo "All test dependencies installed. Run 'pytest' to execute the test suite."
