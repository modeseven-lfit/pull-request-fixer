<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Implementation Guide

This document describes the complete implementation of the `pull-request-fixer`
tool.

## Overview

`pull-request-fixer` is a tool that scans GitHub organizations for blocked
pull requests and automatically fixes their titles and/or bodies based on the
first commit's message.

## Core Functionality

### Command Line Interface

The tool accepts a GitHub organization as the primary argument:

```bash
# Organization name
pull-request-fixer lfreleng-actions --fix-title --fix-body

# Organization URL
pull-request-fixer https://github.com/lfreleng-actions --fix-title
```

You can provide the organization as:

- A simple string: `myorg`
- A GitHub URL: `https://github.com/myorg`
- A GitHub URL with trailing slash:
  `https://github.com/myorg/`

The tool automatically extracts the organization name from URLs.

### Fix Options

Two primary fix options are available:

#### `--fix-title`

Extracts the first line (subject) of the first commit message and sets it as
the PR title.

**Example:**

If the first commit has message:

```text
Fix authentication bug in login handler

This commit addresses an issue where users couldn't
log in with special characters in passwords.

Signed-off-by: John Doe <john@example.com>
```

This sets the PR title to:

```text
Fix authentication bug in login handler
```

#### `--fix-body`

Extracts the body of the first commit message (excluding trailers) and sets it
as the PR description.

**Trailers Removed:**

The following trailer patterns are automatically removed:

- `Signed-off-by:`
- `Co-authored-by:`
- `Reviewed-by:`
- `Tested-by:`
- `Acked-by:`
- `Cc:`
- `Reported-by:`
- `Suggested-by:`
- `Fixes:`
- `See-also:`
- `Link:`
- `Bug:`
- `Change-Id:`

**Example:**

Using the same commit message above, this sets the PR body to:

```text
This commit addresses an issue where users couldn't
log in with special characters in passwords.
```

(The tool removes the `Signed-off-by:` trailer)

### Other Options

- `--dry-run`: Preview changes without applying them
- `--include-drafts`: Include draft PRs in the scan
- `--workers N`: Number of parallel workers (default: 4, max: 32)
- `--verbose`: Enable verbose output
- `--quiet`: Suppress all output except errors
- `--token`: GitHub token (or set `GITHUB_TOKEN` environment
  variable)

## Architecture

### Component Overview

```text
┌──────────────────────────────────────────────────────────┐
│                       CLI (cli.py)                       │
│  - Parse arguments                                       │
│  - Extract organization from URL                         │
│  - Orchestrate scanning and fixing                       │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ├──────────────────┬──────────────────────┐
                 │                  │                      │
                 ▼                  ▼                      ▼
         ┌───────────────┐  ┌──────────────┐   ┌─────────────────┐
         │   PRScanner   │  │   PRFixer    │   │ ProgressTracker │
         │ (pr_scanner)  │  │ (pr_fixer)   │   │ (progress_...)  │
         └───────┬───────┘  └──────┬───────┘   └─────────────────┘
                 │                  │
                 └──────────┬───────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  GitHubClient    │
                  │ (github_client)  │
                  └──────────────────┘
                            │
                            ▼
                     GitHub GraphQL/REST API
```

### Process Flow

1. **Organization Extraction**: Parse the organization argument and extract
   the org name from URLs if needed

2. **Scanning Phase**:
   - Use `PRScanner` to scan the organization for blocked PRs
   - Scanner uses GraphQL queries for efficiency
   - Results stream as the scanner discovers them
   - Progress tracking displays updates

3. **Processing Phase**:
   - The tool processes each blocked PR in parallel (up to `--workers` concurrent)
   - For each PR:
     - Fetch the first commit using REST API
     - Parse commit message into subject and body
     - Remove trailers from body
     - Compare with current PR title/body
     - Apply changes if needed (unless `--dry-run`)

4. **Reporting Phase**:
   - Display summary of changes made
   - Report any errors encountered
   - Exit with appropriate status code

### Parallel Processing

The tool uses asyncio with semaphores for bounded concurrency:

```python
semaphore = asyncio.Semaphore(workers)

async def process_pr(...):
    async with semaphore:
        # Process PR
        ...

# Create tasks for all PRs
tasks = [process_pr(...) for pr in blocked_prs]

# Execute in parallel with bounded concurrency
results = await asyncio.gather(*tasks, return_exceptions=True)
```

This ensures:

- High performance through parallelism
- Controlled API rate limit usage
- Graceful error handling (one PR failure doesn't stop others)

## Implementation Details

### URL Parsing

The `extract_org_from_url()` function handles organization extraction:

```python
def extract_org_from_url(target: str) -> str:
    """Extract organization name from GitHub URL or return as-is."""
    target = target.rstrip("/")

    if "github.com" in target:
        parts = target.split("github.com/")
        if len(parts) > 1:
            path = parts[1]
            org = path.split("/")[0]
            return org

    return target
```

Supports:

- `myorg` → `myorg`
- `https://github.com/myorg` → `myorg`
- `https://github.com/myorg/` → `myorg`
- `github.com/myorg` → `myorg`

### Commit Message Parsing

The `parse_commit_message()` function splits commit messages:

```python
def parse_commit_message(message: str) -> tuple[str, str]:
    """Parse a commit message into subject and body."""
    lines = message.split("\n")

    # First line is the subject
    first_line = lines[0].strip()

    # Rest is body, with trailers removed
    body_lines = lines[1:]
    # ... (skip empty lines, remove trailers)
```

Key features:

- Handles multi-line bodies
- Removes leading/trailing empty lines
- Strips all common Git trailers
- Preserves formatting within the body

### GitHub API Integration

#### GraphQL Queries

Used for efficient organization scanning:

```graphql
query OrgReposOnly($orgName: String!, $reposPerPage: Int!) {
  organization(login: $orgName) {
    repositories(first: $reposPerPage) {
      totalCount
      pageInfo { ... }
      nodes { ... }
    }
  }
}
```

Benefits:

- Single query gets all needed data
- Pagination support for large orgs
- Queries repos with open PRs

#### REST API Endpoints

Used for PR operations:

- `GET /repos/{owner}/{repo}/pulls/{number}/commits` - Get PR commits
- `PATCH /repos/{owner}/{repo}/pulls/{number}` - Update PR title/body

### Error Handling

Three layers of error handling:

1. **CLI Level**: Validates arguments, displays helpful error messages
2. **Processing Level**: Each PR processed independently, errors don't stop others
3. **API Level**: Network errors, rate limiting, authentication handled appropriately
4. **Scanner Level**: Repository-level errors logged but don't stop scan

Example:

```python
try:
    # Process PR
    result = await process_pr(...)
except Exception as e:
    console.print(f"[red]❌ Error: {e}[/red]")
    return False  # Continue with next PR
```

### Progress Tracking

Real-time progress updates:

```text
🔍 Scanning organization: myorg
🔧 Will fix: titles, bodies
🏃 Dry run mode: no changes made

📊 Found 15 blocked PRs to process

🔍 Blocked PRs:
   • myorg/repo1#123: Fix bug
   • myorg/repo2#456: Add feature
   ...

🔄 Processing: myorg/repo1#123
   ✅ Updated title: Fix authentication bug
   ✅ Updated body

✅ Fixed 15 PR(s)
```

## Configuration

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token (required)

### Command Line Flags

You can specify all options on the command line:

```bash
pull-request-fixer myorg \
  --fix-title \
  --fix-body \
  --workers 8 \
  --dry-run \
  --verbose
```

### Token Requirements

The GitHub token needs these permissions:

- `repo` (full control of private repositories)
- Or `public_repo` (for public repositories)

## Usage Examples

### Basic Usage

Fix titles:

```bash
export GITHUB_TOKEN=ghp_xxx
pull-request-fixer lfreleng-actions --fix-title
```

Fix both titles and bodies:

```bash
pull-request-fixer lfreleng-actions --fix-title --fix-body
```

### Dry Run Mode

Preview changes without applying:

```bash
pull-request-fixer lfreleng-actions --fix-title --fix-body --dry-run
```

Output:

```text
🔍 Scanning organization: lfreleng-actions
🔧 Will fix: titles, bodies
🏃 Dry run mode: no changes made

...

🔄 Processing: lfreleng-actions/repo#123
   Would update title:
     From: Update documentation
     To:   docs: Add usage examples for CLI
   Would update body
     Length: 245 chars

✅ [DRY RUN] Would fix 15 PR(s)
```

### Performance Tuning

Use more workers for large organizations:

```bash
pull-request-fixer myorg --fix-title --fix-body --workers 16
```

### Include Draft PRs

By default, the tool excludes draft PRs:

```bash
pull-request-fixer myorg --fix-title --include-drafts
```

### Quiet Mode

Minimal output for automation:

```bash
pull-request-fixer myorg --fix-title --quiet
```

## Testing

### Manual Testing

1. Create a test organization with PRs
2. Ensure PRs have commits with proper messages
3. Run with `--dry-run` first to verify behavior
4. Apply changes without `--dry-run`

### URL Parsing Tests

```bash
python -c "
from pull_request_fixer.cli import extract_org_from_url
assert extract_org_from_url('myorg') == 'myorg'
assert extract_org_from_url('https://github.com/myorg') == 'myorg'
assert extract_org_from_url('https://github.com/myorg/') == 'myorg'
print('✅ URL parsing tests passed')
"
```

### Commit Message Parsing Tests

```bash
python -c "
from pull_request_fixer.cli import parse_commit_message

msg = '''Fix bug in parser

This is the body.

Signed-off-by: John Doe'''

subject, body = parse_commit_message(msg)
assert subject == 'Fix bug in parser'
assert body == 'This is the body.'
assert 'Signed-off-by' not in body
print('✅ Parser tests passed')
"
```

## Troubleshooting

### Common Issues

**Issue**: "No blocked PRs found"

- **Solution**: The organization may not have any blocked PRs, or you may need
  to adjust the scanner definition of "blocked"

**Issue**: "GitHub token required"

- **Solution**: Set `GITHUB_TOKEN` environment variable or use `--token` flag

**Issue**: "Rate limit exceeded"

- **Solution**: Reduce `--workers` count or wait for rate limit to reset

**Issue**: "Could not retrieve commit info"

- **Solution**: PR may not have any commits yet, or commits may not be accessible

**Issue**: "Failed to update PR title/body"

- **Solution**: Check token permissions, user may not have write access to repository

### Debug Mode

Enable verbose logging:

```bash
pull-request-fixer myorg --fix-title --verbose --log-level DEBUG
```

## Performance Characteristics

### Memory Usage

- **Low**: Streaming results, PRs processed as discovered
- **Scales**: O(workers) memory for parallel processing
- **Efficient**: No need to load entire org into memory

### Network Usage

- **Efficient**: GraphQL for bulk queries, REST for updates
- **Parallel**: PRs processed concurrently
- **Respectful**: Bounded concurrency prevents API abuse

### Time Complexity

- **Organization scan**: O(repositories) with parallel processing
- **PR processing**: O(blocked_prs / workers) with parallelism
- **Typical**: About 2-5 seconds per repository, depending on PR count

Example timing for organization with 100 repos, 50 blocked PRs, 8 workers:

- Scanning: ~30-60 seconds
- Processing: ~20-30 seconds
- Total: ~50-90 seconds

## Future Enhancements

Potential additions:

1. **Custom Commit Selection**: Allow fixing from last commit instead of first
2. **Regex Patterns**: Support custom patterns for trailer removal
3. **Template Support**: Use templates for PR body formatting
4. **Multi-Commit**: Combine commit messages from all commits
5. **Auto-merge**: Optionally auto-merge after fixing
6. **Webhook Support**: Trigger on PR events
7. **Configuration File**: Support `.pull-request-fixer.yml` config
8. **PR Filters**: Filter by labels, authors, status checks

## Security Considerations

1. **Token Storage**: Never hardcode tokens, use environment variables
2. **Token Permissions**: Use the required permissions
3. **Rate Limiting**: Respect GitHub's rate limits with bounded concurrency
4. **Validation**: The tool validates and sanitizes all user inputs
5. **Error Messages**: Don't expose sensitive information in errors

## Contributing

When contributing to this tool:

1. Maintain backward compatibility with existing flags
2. Add tests for new functionality
3. Update this documentation
4. Follow existing code style
5. Use type hints throughout
6. Handle errors appropriately

## License

Apache-2.0

## Support

For issues, questions, or feature requests:

- GitHub Issues: <https://github.com/lfit/pull-request-fixer/issues>
- Documentation: <https://github.com/lfit/pull-request-fixer/blob/main/README.md>
