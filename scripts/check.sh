#!/bin/bash
# Check code formatting without making changes

set -e

echo "Checking import sorting with isort..."
uv run isort --check-only --diff .

echo "Checking code formatting with Black..."
uv run black --check --diff .

echo "All checks passed!"
