# Frontend Changes: Theme Toggle Button

## Overview
Added a dark/light theme toggle button to the Course Materials Assistant interface, allowing users to switch between dark and light themes.

## Files Modified

### 1. `frontend/index.html`
- Added theme toggle button element before the main container
- Button includes SVG icons for sun (light mode indicator) and moon (dark mode indicator)
- Includes accessibility attributes (`aria-label`, `title`)
- Updated cache-busting version numbers (v9 → v10)

### 2. `frontend/style.css`
**New Light Theme CSS Variables:**
- Added `[data-theme="light"]` selector with light theme colors:
  - `--background: #f8fafc` (light gray-blue background)
  - `--surface: #ffffff` (white surfaces)
  - `--surface-hover: #f1f5f9` (light hover state)
  - `--text-primary: #1e293b` (dark text for contrast)
  - `--text-secondary: #64748b` (muted secondary text)
  - `--border-color: #e2e8f0` (light borders)
  - `--assistant-message: #f1f5f9` (light message bubbles)
  - `--code-bg: rgba(0, 0, 0, 0.05)` (subtle code background)

**Theme Toggle Button Styles:**
- Fixed position in top-right corner (`top: 1rem; right: 1rem`)
- Circular button design (44px diameter)
- Smooth hover effects with scale transform
- Focus states for accessibility
- Icon transition animations (rotate + scale on theme change)
- Responsive adjustments for mobile (smaller size on screens < 768px)

**Updated Existing Styles:**
- Changed code block backgrounds from hardcoded `rgba(0, 0, 0, 0.2)` to `var(--code-bg)` variable

### 3. `frontend/script.js`
**New Theme Management Functions:**
- `initializeTheme()`: Initializes theme based on localStorage or system preference
- `setTheme(theme)`: Applies theme by setting `data-theme` attribute on document root
- `toggleTheme()`: Switches between dark and light themes, saves to localStorage
- `updateThemeToggleAriaLabel(theme)`: Updates aria-label for screen readers

**Event Listeners Added:**
- Click handler for theme toggle button
- Keyboard handler (Enter/Space) for accessibility
- System preference change listener for auto-switching when no manual preference set

## Features

### Design
- Sun icon displayed in dark mode (click to switch to light)
- Moon icon displayed in light mode (click to switch to dark)
- Smooth 0.3s transition animations on theme change
- Icon rotation and scale effects during transition
- Consistent with existing design aesthetic (uses CSS variables, matches button styling)

### Accessibility
- Keyboard navigable (Tab to focus, Enter/Space to activate)
- Dynamic `aria-label` updates based on current theme
- Focus ring visible on keyboard focus (`:focus-visible`)
- Sufficient color contrast in both themes
- Button has `title` attribute for tooltip

### Persistence
- Theme preference saved to localStorage
- Persists across page reloads and sessions
- Respects system preference if no manual selection made
- Listens for system preference changes

### Responsive Design
- Smaller button size on mobile devices (40px vs 44px)
- Adjusted positioning for smaller screens
- Maintains usability on all device sizes

## Implementation Details

### CSS Custom Properties Strategy
- All theme colors are defined as CSS variables in `:root` (dark theme default)
- Light theme overrides defined under `[data-theme="light"]` selector
- Existing styles already use `var(--variable-name)` syntax, ensuring automatic theme adaptation

### Theme Switching Mechanism
- `data-theme` attribute applied to `<html>` element (`document.documentElement`)
- Dark theme: no `data-theme` attribute (uses `:root` defaults)
- Light theme: `data-theme="light"` triggers CSS variable overrides

### Elements Verified for Both Themes
- Body and container backgrounds
- Sidebar and main chat area surfaces
- Chat messages (user and assistant)
- Input fields and buttons
- Collapsible sections (course stats, suggested questions)
- Code blocks and preformatted text
- Error and success messages
- Scrollbar styling
- Focus rings and hover states

### Visual Hierarchy Preserved
- Primary color (`#2563eb`) consistent across both themes
- Contrast ratios meet WCAG AA standards
- Shadows adjusted for appropriate depth perception in each theme
- Border colors adapted to maintain visual separation

---

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
