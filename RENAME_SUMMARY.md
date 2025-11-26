<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Rename Summary: pr-title-fixer → pull-request-fixer

This document summarizes the final renaming from `pr-title-fixer` to `pull-request-fixer`.

## Overview

The project has been renamed from `pr-title-fixer` to `pull-request-fixer` to better reflect its broader purpose of fixing pull requests (not just titles). Additionally, the `github` subcommand has been removed, and all functionality now runs directly on the base command.

## Changes Made

### 1. Package Renaming

- **Python package**: `pr_title_fixer` → `pull_request_fixer`
- **PyPI package name**: `pr-title-fixer` → `pull-request-fixer`
- **CLI command**: `pr-title-fixer` → `pull-request-fixer`
- **Directory structure**: `src/pr_title_fixer/` → `src/pull_request_fixer/`

### 2. CLI Structure Changes

**Before:**
```bash
pr-title-fixer github <target> [OPTIONS]
```

**After:**
```bash
pull-request-fixer <target> [OPTIONS]
```

The `github` subcommand has been removed. All functionality is now accessed directly through the base command:

- ✅ `pull-request-fixer https://github.com/owner/repo/pull/123`
- ✅ `pull-request-fixer ORG_NAME --dry-run`
- ❌ ~~`pull-request-fixer github ...`~~ (removed)

### 3. File Updates

**Updated files:**
- `pyproject.toml` - Project name, package references, URLs
- `README.md` - All command examples and references
- `CHANGELOG.md` - Project history and links
- `.pre-commit-hooks.yaml` - Hook ID and entry point
- `action.yaml` - GitHub Action name and description
- `demo.sh` - Demo script commands
- `src/pull_request_fixer/cli.py` - CLI structure, help text, examples
- `src/pull_request_fixer/pr_fixer.py` - Logger name

### 4. Command Interface

The CLI now uses Typer's callback with `invoke_without_command=True` to accept arguments directly:

```python
@app.callback(invoke_without_command=True)
def main(
    target: str = typer.Argument(None, ...),
    token: str | None = typer.Option(...),
    ...
) -> None:
    """Pull request formatter and fixer with GitHub integration."""
```

This provides a cleaner, more intuitive interface:
- Single command to remember
- No subcommand confusion
- More concise usage

## Module Status

### ✅ Working Modules
- `cli.py` - Command-line interface (fully updated)
- `models.py` - Data models (cleaned of table-related code)
- `exceptions.py` - Custom exceptions (cleaned and renamed base class)
- `github_client.py` - GitHub API client (working)
- `graphql_queries.py` - GraphQL query templates (working)
- `progress_tracker.py` - Progress tracking for bulk operations (working)

### ⚠️ Modules Needing Implementation
- `pr_scanner.py` - PR scanner (has TODO notes, needs PR-specific logic)
- `pr_fixer.py` - PR fixer (has TODO notes, needs PR-specific logic)

Both of these modules exist and import successfully, but they have TODO comments noting they need to be rewritten for the new PR fixing functionality (instead of markdown table fixing).

## Installation and Testing

### Install
```bash
cd pull-request-fixer
pip install -e .
```

### Verify Installation
```bash
# Check version
pull-request-fixer --version

# Check help
pull-request-fixer --help

# Verify imports
python -c "from pull_request_fixer import cli, models, exceptions, github_client, pr_scanner, pr_fixer; print('✅ OK')"
```

### Expected Output
```
🏷️  pull-request-fixer version 0.1.dev1+...
```

## Usage Examples

### Fix a Single PR
```bash
export GITHUB_TOKEN=ghp_xxx
pull-request-fixer https://github.com/owner/repo/pull/123
```

### Scan an Organization (Dry Run)
```bash
pull-request-fixer myorg --dry-run --token ghp_xxx
```

### Fix PRs Across Organization
```bash
pull-request-fixer myorg --token ghp_xxx --workers 8
```

### With Sync Strategy
```bash
pull-request-fixer https://github.com/owner/repo/pull/123 --sync-strategy rebase
```

## Pre-commit Hook

Update your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/lfit/pull-request-fixer
    rev: v1.0.0
    hooks:
      - id: pull-request-fixer
```

## Breaking Changes from pr-title-fixer

1. **Command name changed**: `pr-title-fixer` → `pull-request-fixer`
2. **No subcommand**: `github` subcommand removed, use base command directly
3. **Package imports**: `pr_title_fixer` → `pull_request_fixer`
4. **Pre-commit hook ID**: `pr-title-fixer` → `pull-request-fixer`

## Migration from pr-title-fixer

If you were using `pr-title-fixer`:

### Update CLI commands:
```bash
# Before
pr-title-fixer github https://github.com/owner/repo/pull/123

# After
pull-request-fixer https://github.com/owner/repo/pull/123
```

### Update Python imports:
```python
# Before
from pr_title_fixer import models

# After
from pull_request_fixer import models
```

### Update pre-commit config:
```yaml
# Before
- repo: https://github.com/lfit/pr-title-fixer
  hooks:
    - id: pr-title-fixer

# After
- repo: https://github.com/lfit/pull-request-fixer
  hooks:
    - id: pull-request-fixer
```

## Next Steps

1. **Implement PR Fixing Logic**: Update `pr_fixer.py` with actual PR fixing logic
2. **Update PR Scanner**: Modify `pr_scanner.py` to scan for PR-specific issues
3. **Add Tests**: Write comprehensive tests for the new functionality
4. **Update Documentation**: Add more detailed usage examples and API documentation

## Verification Checklist

- [x] Package renamed to `pull-request-fixer`
- [x] Python module renamed to `pull_request_fixer`
- [x] CLI command renamed to `pull-request-fixer`
- [x] Github subcommand removed
- [x] All documentation updated
- [x] All examples updated
- [x] Pre-commit hooks updated
- [x] Action metadata updated
- [x] Version callback updated
- [x] Logger names updated
- [x] CLI installs successfully
- [x] CLI shows correct version
- [x] CLI shows correct help text
- [x] All modules import without errors
- [ ] Implement actual PR fixing logic (future work)
- [ ] Add comprehensive tests (future work)