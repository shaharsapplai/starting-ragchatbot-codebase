# Code Quality Tools Setup

## Changes Made

### 1. Updated `pyproject.toml`

Added development dependencies:
- `black>=24.0.0` - Code formatter
- `isort>=5.13.0` - Import sorter

Added tool configurations:
- **[tool.black]**: Configured with 88 character line length, Python 3.13 target, and appropriate exclusions
- **[tool.isort]**: Configured with "black" profile for compatibility

### 2. Created Development Scripts

New `scripts/` directory with the following executable scripts:

- **`scripts/format.sh`**: Formats all Python files using isort and Black
- **`scripts/check.sh`**: Checks formatting without making changes (useful for CI)
- **`scripts/quality.sh`**: Runs all quality checks including formatting and tests

### 3. Formatted Codebase

Applied Black and isort formatting to all Python files:
- 14 files reformatted for consistent style
- Import statements sorted and grouped properly
- Line length standardized to 88 characters

## Usage

```bash
# Install dev dependencies
uv sync --all-extras

# Format all code
./scripts/format.sh

# Check formatting without changes
./scripts/check.sh

# Run all quality checks (formatting + tests)
./scripts/quality.sh

# Or run tools directly
uv run black .
uv run isort .
uv run black --check .
```
