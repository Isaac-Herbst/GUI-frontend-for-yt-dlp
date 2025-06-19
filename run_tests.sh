#!/bin/bash
set -e

echo "Running tests inside Docker container..."

echo "==> Running unit tests..."
python -m unittest discover -s tests -p "test_*.py"