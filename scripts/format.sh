#!/bin/bash
# Format all Python files using Black and isort

set -e

echo "Running isort to sort imports..."
uv run isort .

echo "Running Black to format code..."
uv run black .

echo "Formatting complete!"
