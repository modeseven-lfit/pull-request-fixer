<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Testing Guide

This document provides comprehensive testing instructions for `pull-request-fixer`.

## Prerequisites

1. **GitHub Token**: You need a GitHub personal access token with `repo` scope
2. **Test Repository**: Access to a repository with pull requests
3. **Installation**: `pip install -e .` from the project root

## Setting Up Your Token

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

Or use the `--token` flag:
```bash
pull-request-fixer TARGET --token ghp_xxxxxxxxxxxxx --fix-title
```

## Test Modes

The tool operates in two modes:

### Mode 1: Single PR Processing

Process a specific pull request by providing its URL.

**Syntax:**
```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER [OPTIONS]
```

**Example:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 --fix-title
```

### Mode 2: Organization Scanning

Scan an entire organization for blocked pull requests.

**Syntax:**
```bash
pull-request-fixer ORGANIZATION [OPTIONS]
```

**Examples:**
```bash
# Organization name
pull-request-fixer lfreleng-actions --fix-title

# Organization URL
pull-request-fixer https://github.com/lfreleng-actions --fix-title
```

## Test Cases

### Test 1: Single PR - Title Fix (Dry Run)

**Objective**: Verify the tool can detect title differences and show what it would change.

**Command:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-title \
  --dry-run
```

**Expected Output:**
```
🔍 Processing PR: https://github.com/lfreleng-actions/go-httpbin-action/pull/44
🔧 Will fix: title
🏃 Dry run mode: no changes will be applied

📥 Fetching PR data...

🔄 Processing: lfreleng-actions/go-httpbin-action#44
   Would update title:
     From: Chore: Bump lfreleng-actions/draft-release-promote-action from 0.1.2 to 0.1.3
     To:   Chore: Bump lfreleng-actions/draft-release-promote-action

✅ [DRY RUN] Would fix this PR
```

**Validation:**
- [ ] Tool connects to GitHub API
- [ ] Tool fetches PR #44 data
- [ ] Tool fetches first commit message
- [ ] Tool detects title mismatch
- [ ] Tool shows before/after comparison
- [ ] Tool confirms dry-run (no actual changes)

---

### Test 2: Single PR - Title Fix (Live)

**Objective**: Actually update the PR title.

**Command:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-title
```

**Expected Output:**
```
🔍 Processing PR: https://github.com/lfreleng-actions/go-httpbin-action/pull/44
🔧 Will fix: title

📥 Fetching PR data...

🔄 Processing: lfreleng-actions/go-httpbin-action#44
   ✅ Updated title: Chore: Bump lfreleng-actions/draft-release-promote-action

✅ PR updated successfully
```

**Validation:**
- [ ] Tool updates the PR title on GitHub
- [ ] Tool triggers re-run of failed checks (if any)
- [ ] Visit PR URL and confirm title changed
- [ ] Check that GitHub shows the new title

---

### Test 3: Single PR - Body Fix (Dry Run)

**Objective**: Test PR body extraction and trailer removal.

**Command:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-body \
  --dry-run
```

**Expected Output:**
```
🔍 Processing PR: https://github.com/lfreleng-actions/go-httpbin-action/pull/44
🔧 Will fix: body
🏃 Dry run mode: no changes will be applied

📥 Fetching PR data...

🔄 Processing: lfreleng-actions/go-httpbin-action#44
   Would update body
     Length: XXX chars

✅ [DRY RUN] Would fix this PR
```

**Validation:**
- [ ] Tool extracts commit body
- [ ] Tool removes trailers (Signed-off-by, etc.)
- [ ] Tool shows body length
- [ ] No actual update made

---

### Test 4: Single PR - Both Title and Body

**Objective**: Fix both title and body in one operation.

**Command:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-title \
  --fix-body \
  --dry-run
```

**Expected Output:**
```
🔍 Processing PR: https://github.com/lfreleng-actions/go-httpbin-action/pull/44
🔧 Will fix: title, body
🏃 Dry run mode: no changes will be applied

📥 Fetching PR data...

🔄 Processing: lfreleng-actions/go-httpbin-action#44
   Would update title:
     From: [old title]
     To:   [new title]
   Would update body
     Length: XXX chars

✅ [DRY RUN] Would fix this PR
```

**Validation:**
- [ ] Both title and body detected for update
- [ ] Changes shown separately
- [ ] Dry run confirmed

---

### Test 5: Organization Scan (Dry Run)

**Objective**: Scan entire organization for blocked PRs.

**Command:**
```bash
pull-request-fixer lfreleng-actions \
  --fix-title \
  --dry-run \
  --verbose
```

**Expected Output:**
```
🔍 Scanning organization: lfreleng-actions
🔧 Will fix: title
🏃 Dry run mode: no changes will be applied

📊 Found 15 blocked PRs to process

🔍 Blocked PRs:
   • lfreleng-actions/repo1#123: Title 1
   • lfreleng-actions/repo2#456: Title 2
   ...

🔍 [DRY RUN] Analyzing 15 PRs...

🔄 Processing: lfreleng-actions/repo1#123
   Would update title:
     From: [old]
     To:   [new]

✅ [DRY RUN] Would fix 15 PR(s)
```

**Validation:**
- [ ] Tool scans organization using GraphQL
- [ ] Tool finds blocked PRs
- [ ] Tool displays all found PRs
- [ ] Tool processes each PR
- [ ] Tool reports total that would be fixed

---

### Test 6: Organization Scan (Live, Limited Workers)

**Objective**: Actually fix PRs in organization with controlled concurrency.

**Command:**
```bash
pull-request-fixer lfreleng-actions \
  --fix-title \
  --workers 2 \
  --verbose
```

**Expected Output:**
```
🔍 Scanning organization: lfreleng-actions
🔧 Will fix: title

📊 Found 15 blocked PRs to process

🔧 Processing 15 PRs...

🔄 Processing: lfreleng-actions/repo1#123
   ✅ Updated title: [new title]

🔄 Processing: lfreleng-actions/repo2#456
   ✅ Updated title: [new title]

...

✅ Fixed 15 PR(s)
```

**Validation:**
- [ ] Tool respects worker limit (max 2 concurrent)
- [ ] Tool updates PRs successfully
- [ ] Tool triggers re-runs for updated PRs
- [ ] All PRs processed without errors

---

### Test 7: URL Format Variations

**Objective**: Verify all URL formats work correctly.

**Commands:**
```bash
# Organization name
pull-request-fixer lfreleng-actions --fix-title --dry-run

# Organization URL
pull-request-fixer https://github.com/lfreleng-actions --fix-title --dry-run

# Organization URL with trailing slash
pull-request-fixer https://github.com/lfreleng-actions/ --fix-title --dry-run

# PR URL
pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title --dry-run

# PR URL with /pulls/ (alternate format)
pull-request-fixer https://github.com/owner/repo/pulls/123 --fix-title --dry-run
```

**Validation:**
- [ ] All formats parsed correctly
- [ ] Organization mode vs PR mode detected correctly
- [ ] No errors from URL parsing

---

### Test 8: Error Handling

**Objective**: Verify graceful error handling.

#### Test 8a: Invalid PR URL
```bash
pull-request-fixer https://github.com/invalid/url --fix-title
```

**Expected**: Clear error message about invalid URL format

#### Test 8b: Non-existent PR
```bash
pull-request-fixer https://github.com/owner/repo/pull/999999 --fix-title
```

**Expected**: Error message about PR not found

#### Test 8c: Missing Token
```bash
unset GITHUB_TOKEN
pull-request-fixer myorg --fix-title
```

**Expected**: Error message requesting GitHub token

#### Test 8d: No Fix Options
```bash
pull-request-fixer myorg
```

**Expected**: Warning about needing --fix-title or --fix-body

---

### Test 9: Commit Message Parsing

**Objective**: Verify trailer removal works correctly.

Create a test PR with commit message:
```
Fix authentication bug

This commit fixes an issue where users
couldn't log in properly.

Fixes: #123
Signed-off-by: John Doe <john@example.com>
Co-authored-by: Jane Doe <jane@example.com>
```

**Command:**
```bash
pull-request-fixer https://github.com/owner/repo/pull/TEST --fix-body --dry-run
```

**Expected Body Result:**
```
This commit fixes an issue where users
couldn't log in properly.
```

**Validation:**
- [ ] Trailers removed (Fixes:, Signed-off-by:, Co-authored-by:)
- [ ] Body text preserved
- [ ] Empty lines handled correctly

---

### Test 10: Performance Test

**Objective**: Test parallel processing with many PRs.

**Command:**
```bash
pull-request-fixer large-org \
  --fix-title \
  --workers 16 \
  --verbose
```

**Metrics to Track:**
- Total PRs found
- Time to scan organization
- Time to process all PRs
- Average time per PR
- Number of API calls
- Memory usage

**Expected Performance:**
- ~2-5 seconds per repository for scanning
- ~1-2 seconds per PR for processing
- Linear scaling with worker count (up to API limits)

---

## Verification Checklist

After running tests, verify:

### Functional Requirements
- [ ] Single PR mode works
- [ ] Organization scan mode works
- [ ] Title fixing works correctly
- [ ] Body fixing works correctly
- [ ] Trailers removed from bodies
- [ ] Dry run mode previews without changing
- [ ] Live mode actually updates PRs

### URL Parsing
- [ ] Organization name accepted
- [ ] Organization URL accepted
- [ ] PR URL accepted
- [ ] All URL variations work

### API Integration
- [ ] GraphQL queries work for scanning
- [ ] REST API works for PR operations
- [ ] Authentication works
- [ ] Re-run checks triggered after updates

### Error Handling
- [ ] Invalid URLs caught
- [ ] Missing token detected
- [ ] API errors reported clearly
- [ ] Network errors handled gracefully

### Performance
- [ ] Parallel processing works
- [ ] Worker limit respected
- [ ] No memory leaks
- [ ] Reasonable speed

### Output
- [ ] Progress displayed clearly
- [ ] Dry run clearly marked
- [ ] Success/failure reported
- [ ] Verbose mode provides details
- [ ] Quiet mode minimizes output

---

## Example Test Session

Complete test session verifying all functionality:

```bash
# Set token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Test 1: Single PR dry run
echo "=== Test 1: Single PR Dry Run ==="
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-title --dry-run

# Test 2: Single PR live (if approved)
echo "=== Test 2: Single PR Live ==="
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 \
  --fix-title

# Test 3: Organization dry run
echo "=== Test 3: Organization Dry Run ==="
pull-request-fixer lfreleng-actions --fix-title --dry-run

# Test 4: Organization live with limited workers
echo "=== Test 4: Organization Live ==="
pull-request-fixer lfreleng-actions --fix-title --workers 4

# Test 5: Verify help
echo "=== Test 5: Help System ==="
pull-request-fixer --help

# Test 6: Verify version
echo "=== Test 6: Version ==="
pull-request-fixer --version

echo "=== All Tests Complete ==="
```

---

## Troubleshooting

### Issue: "No such command"
**Solution**: Reinstall the package: `pip install -e .`

### Issue: API rate limit
**Solution**: 
- Reduce workers: `--workers 2`
- Wait for rate limit reset
- Use token with higher limits

### Issue: Authentication failed
**Solution**:
- Verify token is set: `echo $GITHUB_TOKEN`
- Check token has `repo` scope
- Ensure token hasn't expired

### Issue: PR not updating
**Solution**:
- Check token has write access to repository
- Verify PR is not locked
- Check repository is not archived

---

## Continuous Testing

For ongoing development, run these regularly:

```bash
# Quick smoke test
pull-request-fixer --version
pull-request-fixer --help

# URL parsing tests
python -c "from pull_request_fixer.cli import parse_target, extract_pr_info_from_url; \
assert parse_target('myorg') == ('org', 'myorg'); \
assert parse_target('https://github.com/owner/repo/pull/44')[0] == 'pr'; \
print('✅ URL tests passed')"

# Commit parser tests
python -c "from pull_request_fixer.cli import parse_commit_message; \
subject, body = parse_commit_message('Fix bug\n\nBody\n\nSigned-off-by: Test'); \
assert subject == 'Fix bug'; \
assert 'Signed-off-by' not in body; \
print('✅ Parser tests passed')"

# Module imports
python -c "from pull_request_fixer import cli, models, pr_scanner, github_client; \
print('✅ Import tests passed')"
```

---

## Test Data

Example PR that's good for testing:
- **URL**: https://github.com/lfreleng-actions/go-httpbin-action/pull/44
- **Current Title**: "Chore: Bump lfreleng-actions/draft-release-promote-action from 0.1.2 to 0.1.3"
- **First Commit Subject**: "Chore: Bump lfreleng-actions/draft-release-promote-action"
- **Expected Result**: Title shortened to match commit subject

This PR demonstrates:
- Title mismatch (version info in PR title but not in commit)
- Blocked PR status
- Typical dependabot-style PR

---

## Reporting Issues

When reporting issues, include:
1. Command used
2. Full output (use `--verbose`)
3. Expected vs actual behavior
4. GitHub token scope (don't include token!)
5. Organization/PR being processed (if public)

Example issue report:
```
Command: pull-request-fixer myorg --fix-title --verbose
Output: [paste output]
Expected: Title should update
Actual: Error message about permissions
Token scope: repo
Organization: myorg (public)
```
