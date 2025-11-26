<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Migration Notes: markdown-table-fixer → pr-title-fixer

This document describes the migration from `markdown-table-fixer` to `pr-title-fixer`.

## Overview

The `pr-title-fixer` project was forked from `markdown-table-fixer` as a starting point for a new tool focused on fixing pull request titles rather than markdown table formatting.

## Changes Made

### 1. Package Renaming

- **Python package**: `markdown_table_fixer` → `pr_title_fixer`
- **PyPI package name**: `markdown-table-fixer` → `pr-title-fixer`
- **CLI command**: `markdown-table-fixer` → `pr-title-fixer`
- **Directory structure**: `src/markdown_table_fixer/` → `src/pr_title_fixer/`

### 2. CLI Commands

**Removed:**
- `lint` command - The entire lint subcommand and its associated functionality has been removed, including:
  - File scanning for markdown files
  - Table parsing and validation
  - Local file fixing capabilities
  - Text and JSON output formats for file results

**Retained:**
- `github` command - Updated to focus on PR title fixing instead of markdown tables
  - Command signature remains the same
  - Now described as "Fix PR titles in GitHub pull requests"
  - Examples updated to reflect PR title fixing use case

### 3. Code Cleanup

**Removed imports and functions (from cli.py):**
- `json` module (no longer needed)
- `FileAccessError` and `TableParseError` exceptions
- `FileResult`, `OutputFormat`, `ScanResult`, `TableViolation` models
- `FileFixer`, `MarkdownFileScanner`, `TableParser`, `TableValidator` classes
- `_process_file()` helper function
- `_output_json_results()` helper function
- `_output_text_results()` helper function

**Note:** While these imports were removed from `cli.py`, the underlying modules still exist in the codebase and may be useful for future functionality or can be removed entirely.

### 4. Documentation Updates

**Updated files:**
- `README.md` - Completely rewritten for PR title fixer use case
- `CHANGELOG.md` - Updated project history and links
- `pyproject.toml` - Updated project metadata, URLs, and keywords
- `.pre-commit-hooks.yaml` - Updated hook definitions (removed check variant)
- `action.yaml` - Updated GitHub Action metadata
- `demo.sh` - Updated demo script for new functionality
- Test imports updated in `tests/test_table_parser.py` and `tests/test_unicode_width.py`

### 5. Configuration Updates

**pyproject.toml changes:**
- Project name: `pr-title-fixer`
- Description: "PR title formatter and fixer with GitHub integration"
- Keywords: Focus on PR/pull-request instead of markdown/table
- URLs: Updated to point to `lfit/pr-title-fixer` repository
- Script entry point: `pr-title-fixer = "pr_title_fixer.cli:app"`
- Coverage and lint configurations updated for new package name

## Files Removed

The following table-related files have been completely removed:
- `table_parser.py` - Markdown table parsing logic (deleted)
- `table_validator.py` - Table validation rules (deleted)
- `table_fixer.py` - Table fixing logic (deleted)
- `tests/test_table_parser.py` - Table parser tests (deleted)
- `tests/test_unicode_width.py` - Unicode width tests (deleted)
- `examples/bad_tables.md` - Example files (deleted)
- `examples/emoji_tables.md` - Example files (deleted)

## Files Cleaned Up

The following files had table-related code removed:
- `models.py` - Removed all table-related models (`TableCell`, `TableRow`, `MarkdownTable`, `TableViolation`, `TableFix`, `FileResult`, `ScanResult`, `ViolationType`, `CLIOptions`)
- `exceptions.py` - Removed table-related exceptions (`TableParseError`, `TableValidationError`, `FixError`, `MarkdownLintError`) and renamed base class from `MarkdownTableFixerError` to `PRTitleFixerError`
- `pyproject.toml` - Removed `wcwidth` dependency (was only used for table cell width calculations)

## Files Marked for Future Updates

The following files still reference table functionality and need to be rewritten:
- `pr_fixer.py` - Has TODO comments noting it needs to be rewritten for PR title fixing
- `pr_scanner.py` - Has TODO comments noting it needs to be updated for PR title scanning

## Testing

All table-related tests have been removed:
- `tests/test_table_parser.py` - Deleted (22 tests removed)
- `tests/test_unicode_width.py` - Deleted (10 tests removed)

The `tests/` directory now only contains `__init__.py`. New tests need to be written for PR title functionality.

## Next Steps

To complete the transition to a PR title fixer:

1. **Implement PR Title Logic:**
   - Define PR title formatting rules (e.g., Conventional Commits)
   - Create PR title validation logic
   - Implement PR title fixing logic

2. **Update GitHub Command:**
   - Modify the `github` command to actually fix PR titles
   - Update the PR scanner to identify PRs with title issues
   - Update the PR fixer to apply title corrections

3. **Clean Up Remaining Code:**
   - ✅ Removed table-related modules
   - ✅ Removed unused models and exceptions
   - ✅ Removed table-related tests
   - Rewrite `pr_fixer.py` for PR title fixing
   - Rewrite `pr_scanner.py` for PR title scanning

4. **Add New Tests:**
   - Unit tests for PR title validation
   - Unit tests for PR title fixing
   - Integration tests for GitHub operations

5. **Update Documentation:**
   - Add examples of PR title formats
   - Document the title fixing rules
   - Add troubleshooting guide

## Verification

To verify the migration was successful:

```bash
# Install the package
pip install -e .

# Check version
pr-title-fixer --version

# Check help
pr-title-fixer --help
pr-title-fixer github --help

# Verify imports work
python -c "from pr_title_fixer import cli, models, exceptions, github_client; print('✅ Imports work')"
```

Expected output:
- CLI command should be `pr-title-fixer` (not `markdown-table-fixer`)
- Only `github` command should be available (no `lint` command)
- Version string should show "pr-title-fixer"
- Core modules should import without errors

Note: There are currently no tests in the `tests/` directory. New tests need to be written for PR title functionality.

## Breaking Changes

For users of the original `markdown-table-fixer`:

1. **Package name changed** - Update imports from `markdown_table_fixer` to `pr_title_fixer`
2. **CLI command changed** - Use `pr-title-fixer` instead of `markdown-table-fixer`
3. **Lint command removed** - The entire lint functionality is gone
4. **Pre-commit hooks changed** - Update `.pre-commit-config.yaml` to use new repository and hook IDs

## Migration Checklist

- [x] Rename Python package directory
- [x] Update pyproject.toml
- [x] Update all Python imports
- [x] Remove lint command from CLI
- [x] Remove lint helper functions
- [x] Update CLI app name and help text
- [x] Update README.md
- [x] Update CHANGELOG.md
- [x] Update .pre-commit-hooks.yaml
- [x] Update action.yaml
- [x] Update demo.sh
- [x] Update test imports
- [x] Verify CLI works
- [x] Verify tests pass
- [x] Remove table-related modules (`table_parser.py`, `table_validator.py`, `table_fixer.py`)
- [x] Remove table-related tests
- [x] Remove table-related models and exceptions
- [x] Remove wcwidth dependency
- [x] Remove example files
- [x] Add TODO comments to `pr_fixer.py` and `pr_scanner.py`
- [ ] Implement PR title fixing logic (future work)
- [ ] Rewrite `pr_fixer.py` for PR titles (future work)
- [ ] Rewrite `pr_scanner.py` for PR titles (future work)
- [ ] Add new tests for PR title functionality (future work)