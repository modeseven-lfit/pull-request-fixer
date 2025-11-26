<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# PR Scanner Update

This document describes the update to `pr_scanner.py` based on the dependamerge tool's scanning patterns.

## Overview

The `pr_scanner.py` module has been rewritten to follow the proven patterns from the dependamerge project's `GitHubService` class. This provides a robust, efficient way to scan GitHub organizations for pull requests.

## What Changed

### Before
The previous `pr_scanner.py` had TODO notes indicating it was still focused on markdown table scanning and needed to be updated for general PR scanning.

### After
The new implementation provides:
- Clean, focused PR scanning logic
- Efficient GraphQL-based queries
- Parallel processing with bounded concurrency
- Proper progress tracking integration
- Streaming results via async iterators

## Key Features

### 1. Efficient Organization Scanning

```python
async for owner, repo_name, pr_data in scanner.scan_organization(
    "myorg", include_drafts=False
):
    # Process each PR as it's discovered
    print(f"Found PR: {owner}/{repo_name}#{pr_data['number']}")
```

The scanner:
- Counts total repositories first (for accurate progress tracking)
- Only queries repositories with open PRs
- Streams results as they're found (no need to load everything into memory)
- Processes repositories in parallel with bounded concurrency

### 2. Bounded Concurrency

```python
scanner = PRScanner(
    client=github_client,
    progress_tracker=tracker,
    max_repo_tasks=8,      # Max concurrent repository scans
    max_page_tasks=16,     # Max concurrent page fetches
)
```

This prevents overwhelming the GitHub API while maintaining good performance.

### 3. Progress Tracking

The scanner integrates with the `ProgressTracker` to provide real-time updates:
- Total repositories found
- Current repository being scanned
- PRs found per repository
- Errors encountered

### 4. Pagination Support

Handles large result sets automatically:
- Fetches first page of PRs for each repository
- Continues fetching additional pages as needed
- Uses cursors for efficient pagination

## Architecture

### Core Methods

#### `scan_organization(organization, include_drafts=False)`
Main entry point that orchestrates the entire scanning process:
1. Counts total repositories
2. Iterates repositories with open PRs
3. Fetches PRs for each repository (with pagination)
4. Yields PRs as they're discovered

#### `_count_org_repositories(organization)`
Efficiently counts total repositories using the `ORG_REPOS_ONLY` GraphQL query.

#### `_iter_org_repositories_with_open_prs(organization)`
Iterates over repositories that have at least one open PR, skipping empty repositories for efficiency.

#### `_fetch_repo_prs_first_page(owner, repo_name)`
Fetches the first page of open PRs for a repository.

#### `_iter_repo_open_prs_pages(owner, repo_name, after_cursor)`
Continues fetching additional pages of PRs using cursor-based pagination.

### Design Patterns

**Producer-Consumer Pattern:**
- Producer task scans repositories and adds PRs to a queue
- Consumer (the async iterator) yields PRs from the queue
- This allows parallel repository scanning while maintaining ordered output

**Semaphore-Based Concurrency:**
- `repo_semaphore`: Limits concurrent repository scans
- `page_semaphore`: Limits concurrent page fetches
- Prevents overwhelming the API while maximizing throughput

**Async Iterator:**
- Returns an `AsyncIterator` instead of loading all results into memory
- Allows processing to start immediately as PRs are found
- More efficient for large organizations

## GraphQL Queries Used

The scanner uses these GraphQL queries from `graphql_queries.py`:

1. **ORG_REPOS_ONLY**: Lightweight query to count total repositories
2. **REPO_OPEN_PRS_PAGE**: Fetches repository information with open PRs

These queries are optimized to:
- Request only needed fields
- Use proper pagination
- Support filtering (archived repos, draft PRs, etc.)

## Integration with Existing Code

The scanner works seamlessly with existing components:

### GitHub Client
```python
scanner = PRScanner(
    client=github_client,  # Uses existing GitHubClient
    progress_tracker=tracker,
)
```

### CLI Integration
```python
# In cli.py
scanner = PRScanner(client, progress_tracker=progress_tracker)

async for owner, repo_name, pr_data in scanner.scan_organization(org):
    pr_info = PRInfo(
        number=pr_data.get("number", 0),
        title=pr_data.get("title", ""),
        repository=f"{owner}/{repo_name}",
        url=pr_data.get("html_url", ""),
        author=pr_data.get("user", {}).get("login", ""),
        is_draft=pr_data.get("draft", False),
        # ... etc
    )
    # Process the PR
```

## Configuration

### Default Values

Based on dependamerge's proven configuration:

```python
DEFAULT_PRS_PAGE_SIZE = 30       # Pull requests per GraphQL page
DEFAULT_FILES_PAGE_SIZE = 50     # Files per pull request (if needed)
DEFAULT_COMMENTS_PAGE_SIZE = 10  # Comments per pull request (if needed)
DEFAULT_CONTEXTS_PAGE_SIZE = 20  # Status contexts per pull request (if needed)
```

### Concurrency Settings

```python
max_repo_tasks = 8   # Concurrent repository scans
max_page_tasks = 16  # Concurrent page fetches
```

These values provide a good balance between speed and API rate limit compliance.

## Error Handling

The scanner includes robust error handling:

- Repository-level errors don't stop the entire scan
- Errors are logged and reported to the progress tracker
- Exceptions during pagination are caught and logged
- Producer-consumer pattern ensures cleanup even on errors

## Performance Characteristics

### Memory Efficient
- Streaming results via async iterator
- No need to load all PRs into memory at once
- Processes PRs as they're discovered

### Network Efficient
- Only queries repositories with open PRs
- Batched GraphQL queries
- Cursor-based pagination
- Bounded concurrency prevents API throttling

### Time Efficient
- Parallel repository processing
- Parallel page fetching
- Early results available immediately

## Differences from Dependamerge

While inspired by dependamerge's `GitHubService`, this implementation:

1. **Simplified**: Focuses only on scanning, not on analysis or merging
2. **Streaming**: Uses async iterator instead of returning complete results
3. **Flexible**: Can be used for any PR processing, not just unmergeability checks
4. **Standalone**: Doesn't include dependamerge-specific logic like:
   - PR similarity checking
   - Branch protection queries
   - File change extraction
   - Review extraction
   - Status check analysis

These features can be added later if needed for specific use cases.

## Testing

To test the scanner:

```python
from pull_request_fixer import PRScanner, GitHubClient

async def test_scan():
    async with GitHubClient(token) as client:
        scanner = PRScanner(client)
        
        count = 0
        async for owner, repo, pr_data in scanner.scan_organization("myorg"):
            count += 1
            print(f"Found PR: {owner}/{repo}#{pr_data['number']}")
        
        print(f"Total PRs found: {count}")

asyncio.run(test_scan())
```

## Future Enhancements

Potential additions based on needs:

1. **Filtering**: Add filters for specific PR criteria (author, labels, status)
2. **Analysis**: Add methods to analyze PRs for specific issues
3. **Caching**: Cache repository data to avoid repeated queries
4. **Metrics**: Collect and report scanning performance metrics
5. **Retry Logic**: Add automatic retry for transient API errors

## Summary

The new `pr_scanner.py` provides a solid foundation for scanning GitHub organizations for pull requests. It follows proven patterns from dependamerge while being simpler and more focused on the specific needs of pull-request-fixer.

Key benefits:
- ✅ Efficient GraphQL-based scanning
- ✅ Parallel processing with bounded concurrency
- ✅ Memory-efficient streaming results
- ✅ Robust error handling
- ✅ Progress tracking integration
- ✅ Clean, maintainable code

The scanner is ready to use and can be extended as needed for specific PR processing requirements.