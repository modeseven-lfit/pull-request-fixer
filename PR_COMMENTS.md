<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# PR Comment Feature

This document describes the automatic PR commenting feature in `pull-request-fixer`.

## Overview

When the tool successfully applies fixes to a pull request (not in dry-run mode), it automatically adds a comment to the PR explaining what was changed. This provides transparency and helps PR authors understand the automated changes.

## Comment Format

The comment follows the same format as `markdown-table-fixer` for consistency across LF tools.

### Basic Format

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request title** updated to match first commit
- **Pull request body** updated to match commit message

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

### Components

1. **Header**: `## 🛠️ Pull Request Fixer`
   - Uses H2 heading with emoji
   - Consistent with other LF tools

2. **Summary Line**: "Automatically fixed pull request metadata:"
   - Explains the purpose of the comment
   - Uses consistent language

3. **Change List**: Bullet points for each fix applied
   - **Title fix**: "**Pull request title** updated to match first commit"
   - **Body fix**: "**Pull request body** updated to match commit message"
   - Bold text highlights what was changed
   - Only includes items that were actually changed

4. **Footer**: Link to tool repository
   - Horizontal rule separator
   - Italicized attribution
   - Link to GitHub repository

## When Comments Are Created

Comments are created when:
- ✅ Fixes are successfully applied (not dry-run mode)
- ✅ At least one change was made (title or body)
- ✅ PR update was successful

Comments are NOT created when:
- ❌ Running in dry-run mode (`--dry-run`)
- ❌ No changes were needed (current title/body already match commit)
- ❌ PR update failed

## Examples

### Example 1: Title Only

When only the PR title is fixed:

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request title** updated to match first commit

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

### Example 2: Body Only

When only the PR body is fixed:

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request body** updated to match commit message

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

### Example 3: Both Title and Body

When both are fixed:

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request title** updated to match first commit
- **Pull request body** updated to match commit message

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

## Real-World Example

For PR https://github.com/lfreleng-actions/go-httpbin-action/pull/44:

**Before:**
- Title: "Chore: Bump lfreleng-actions/draft-release-promote-action from 0.1.2 to 0.1.3"

**Command:**
```bash
pull-request-fixer https://github.com/lfreleng-actions/go-httpbin-action/pull/44 --fix-title
```

**After:**
- Title: "Chore: Bump lfreleng-actions/draft-release-promote-action"
- Comment added to PR:

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request title** updated to match first commit

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

## Implementation Details

### Function: `create_pr_comment()`

Located in `src/pull_request_fixer/cli.py`

```python
async def create_pr_comment(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    changes_made: list[str],
) -> None:
    """Create a comment on the PR summarizing the fixes applied."""
```

### API Endpoint

Uses GitHub REST API:
- **Endpoint**: `POST /repos/{owner}/{repo}/issues/{pr_number}/comments`
- **Authentication**: GitHub token with `repo` scope
- **Payload**: JSON with `body` field containing comment markdown

### Error Handling

Comment creation is **best-effort**:
- Failures are silently ignored
- Won't prevent PR updates from succeeding
- Ensures tool remains robust even if commenting fails

Reasons commenting might fail:
- Token lacks comment permissions
- Network issues
- Rate limiting
- Repository settings restrict comments

## Benefits

### For PR Authors
- **Transparency**: Clear explanation of what changed
- **Context**: Understand why the PR was modified
- **Traceability**: Link back to the tool for more information

### For Reviewers
- **Visibility**: See at a glance what was automated
- **Audit Trail**: Comments remain as permanent record
- **Consistency**: Standard format across all LF tools

### For Organizations
- **Accountability**: Clear attribution of automated changes
- **Documentation**: Built-in documentation of automation actions
- **Trust**: Transparent automation builds confidence

## Consistency with Other Tools

This format matches the style used by:
- **markdown-table-fixer**: Uses same H2 header, emoji, and footer format
- **dependamerge**: Similar commenting pattern for automated merges
- **Other LF tools**: Consistent branding and attribution

## Configuration

Currently, PR comments are:
- ✅ Always enabled when fixes are applied
- ✅ Never created in dry-run mode
- ✅ Best-effort (failures don't stop PR updates)

Future enhancements could add:
- `--no-comment` flag to disable comments
- `--comment-template` for custom comment formats
- Configuration file for comment customization

## Testing

To test the comment feature:

```bash
# Test with single PR
pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title

# Verify:
# 1. PR title was updated
# 2. Comment was added to PR
# 3. Comment has correct format
```

**Expected result:**
- Comment appears at bottom of PR conversation
- Comment shows which changes were made
- Comment includes link to tool repository

## Troubleshooting

### Comment not appearing?

Check:
1. **Not in dry-run**: Comments only in live mode
2. **Changes applied**: Only if fixes were actually made
3. **Token permissions**: Ensure `repo` scope includes comment permissions
4. **Repository settings**: Check if comments are allowed

### Comment has wrong format?

This shouldn't happen, but if it does:
1. Check tool version: `pull-request-fixer --version`
2. Report issue with PR URL and observed format
3. Include command used and any error messages

## Future Enhancements

Potential additions:
1. **Detailed change summary**: Show before/after for title changes
2. **Commit reference**: Link to the specific commit used
3. **Customizable templates**: Allow organizations to customize format
4. **Multiple fix tracking**: If tool runs multiple times, update existing comment
5. **Mention authors**: Optionally @mention PR author in comment

## Related Documentation

- **README.md**: User guide with PR comment section
- **IMPLEMENTATION.md**: Technical details of commenting implementation
- **TESTING.md**: Test procedures including comment verification

## See Also

- **markdown-table-fixer**: Similar commenting implementation
- **GitHub API Documentation**: Issue comments endpoint
- **LF Tool Standards**: Consistent formatting across tools