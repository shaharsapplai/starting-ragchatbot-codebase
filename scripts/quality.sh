#!/bin/bash
# Run all code quality checks including tests

set -e

echo "=== Code Quality Checks ==="
echo ""

echo "1. Checking import sorting with isort..."
uv run isort --check-only --diff .
echo "   Import sorting: OK"
echo ""

echo "2. Checking code formatting with Black..."
uv run black --check --diff .
echo "   Code formatting: OK"
echo ""

echo "3. Running tests with pytest..."
cd backend && uv run pytest -v
echo "   Tests: OK"
echo ""

echo "=== All quality checks passed! ==="
