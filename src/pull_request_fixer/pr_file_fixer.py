# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Fix files in pull requests by cloning, modifying, and pushing changes.

This module provides functionality for fixing files in GitHub pull requests
by cloning the PR branch, applying regex-based modifications, amending the
commit, and force-pushing the changes back.
"""

from __future__ import annotations

from contextlib import suppress
import logging
from pathlib import Path
import re
import subprocess
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .github_client import GitHubClient
    from .models import GitHubFixResult, PRInfo


class PRFileFixer:
    """Fixes files in pull requests using Git operations."""

    def __init__(self, client: GitHubClient) -> None:
        """Initialize PR file fixer.

        Args:
            client: GitHub API client for authentication and API calls
        """
        self.client = client
        self.logger = logging.getLogger("pull_request_fixer.pr_file_fixer")

    def _sanitize_message(self, message: str) -> str:
        """Remove sensitive information from messages.

        Args:
            message: Message that may contain tokens

        Returns:
            Sanitized message with tokens removed
        """
        # Remove common token patterns
        patterns = [
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub personal access tokens
            r"ghs_[a-zA-Z0-9]{36}",  # GitHub server tokens
            r"github_pat_[a-zA-Z0-9_]{82}",  # GitHub fine-grained tokens
            r"https://[^:]+:[^@]+@",  # URLs with credentials
            r"x-access-token:[^@]+@",  # Git auth tokens
        ]

        sanitized = message
        for pattern in patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)

        return sanitized

    async def fix_pr_by_url(
        self,
        pr_url: str,
        file_pattern: str,
        search_pattern: str,
        replacement: str,
        *,
        remove_lines: bool = False,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
    ) -> GitHubFixResult:
        """Fix files in a PR by URL, amending the existing commit.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            file_pattern: Regex pattern to match file paths
            search_pattern: Regex pattern to search for in files
            replacement: Replacement string (or empty for line removal)
            remove_lines: If True, remove matching lines entirely
            context_start: Optional regex to define context start for line removal
            context_end: Optional regex to define context end for line removal
            dry_run: If True, don't actually push changes

        Returns:
            GitHubFixResult with operation details
        """
        from .models import GitHubFixResult, PRInfo

        # Parse PR URL
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url
        )
        if not match:
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=0,
                    title="",
                    repository="",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=f"Invalid PR URL format: {pr_url}",
            )

        owner, repo, pr_number_str = match.groups()
        pr_number = int(pr_number_str)

        self.logger.debug(f"Processing PR: {owner}/{repo}#{pr_number}")

        try:
            # Get PR details
            pr_data = await self.client._request(
                "GET", f"/repos/{owner}/{repo}/pulls/{pr_number}"
            )

            if not isinstance(pr_data, dict):
                return GitHubFixResult(
                    pr_info=PRInfo(
                        number=pr_number,
                        title="",
                        repository=f"{owner}/{repo}",
                        url=pr_url,
                        author="",
                        is_draft=False,
                        head_ref="",
                        head_sha="",
                        base_ref="",
                        mergeable="",
                        merge_state_status="",
                    ),
                    success=False,
                    message="Failed to fetch PR data",
                )

            head = pr_data.get("head", {})
            head_sha = head.get("sha", "")
            head_ref = head.get("ref", "")
            head_repo = head.get("repo", {})
            clone_url = head_repo.get("clone_url", "")

            pr_info = PRInfo(
                number=pr_number,
                title=pr_data.get("title", ""),
                repository=f"{owner}/{repo}",
                url=pr_url,
                author=pr_data.get("user", {}).get("login", ""),
                is_draft=pr_data.get("draft", False),
                head_ref=head_ref,
                head_sha=head_sha,
                base_ref=pr_data.get("base", {}).get("ref", ""),
                mergeable=pr_data.get("mergeable", "unknown"),
                merge_state_status=pr_data.get("mergeable_state", "unknown"),
            )

            if not clone_url:
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message="PR head repository not accessible",
                )

            # Clone and fix using Git operations
            return await self._fix_pr_with_git(
                pr_info,
                clone_url,
                owner,
                repo,
                file_pattern,
                search_pattern,
                replacement,
                remove_lines=remove_lines,
                context_start=context_start,
                context_end=context_end,
                dry_run=dry_run,
            )

        except Exception as e:
            self.logger.error(f"Error fixing PR: {e}", exc_info=True)
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=pr_number,
                    title="",
                    repository=f"{owner}/{repo}",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=str(e),
                error=str(e),
            )

    async def _fix_pr_with_git(  # noqa: PLR0911
        self,
        pr_info: PRInfo,
        clone_url: str,
        owner: str,
        repo: str,
        file_pattern: str,
        search_pattern: str,
        replacement: str,
        *,
        remove_lines: bool = False,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
    ) -> GitHubFixResult:
        """Fix PR using Git operations (clone, fix, amend, push).

        Args:
            pr_info: PR information
            clone_url: Repository clone URL
            owner: Repository owner
            repo: Repository name
            file_pattern: Regex pattern to match file paths
            search_pattern: Regex pattern to search for
            replacement: Replacement string
            remove_lines: If True, remove matching lines entirely
            context_start: Optional context start for line removal
            context_end: Optional context end for line removal
            dry_run: If True, don't push changes

        Returns:
            GitHubFixResult with operation details
        """
        from .file_fixer import FileFixer
        from .models import GitHubFixResult

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            self.logger.debug(f"Cloning {clone_url} to {repo_dir}")

            try:
                # Clone the repository with authentication
                # Note: The token is embedded in the URL for git operations.
                # While this is the standard approach for HTTPS git authentication,
                # we ensure all error messages are sanitized via _sanitize_message()
                # to prevent token exposure in logs or error output.
                auth_url = clone_url.replace(
                    "https://", f"https://x-access-token:{self.client.token}@"
                )
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        pr_info.head_ref,
                        auth_url,
                        str(repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Find and fix files
                fixer = FileFixer()
                matching_files = fixer.find_files(repo_dir, file_pattern)

                self.logger.debug(
                    f"Found {len(matching_files)} files matching pattern"
                )

                files_modified: list[Path] = []
                file_modifications: list[FileModification] = []
                total_changes = 0

                for file_path in matching_files:
                    self.logger.debug(f"Processing {file_path}")

                    if remove_lines:
                        # Use line removal mode
                        was_modified, original, modified = (
                            fixer.remove_lines_matching(
                                file_path,
                                search_pattern,
                                context_start=context_start,
                                context_end=context_end,
                                dry_run=False,  # Always apply to temp dir
                            )
                        )
                    else:
                        # Use regex replacement mode
                        was_modified, original, modified = fixer.apply_fix(
                            file_path,
                            search_pattern,
                            replacement,
                            dry_run=False,  # Always apply to temp dir
                        )

                    if was_modified:
                        from .models import FileModification

                        files_modified.append(file_path)
                        file_modifications.append(
                            FileModification(
                                file_path=file_path,
                                original_content=original,
                                modified_content=modified,
                            )
                        )
                        total_changes += 1
                        self.logger.debug(f"Modified {file_path.name}")

                # Handle no files modified or dry-run mode
                if not files_modified:
                    message = "No files required changes"
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message=message,
                        files_modified=[],
                        file_modifications=[],
                    )

                if dry_run:
                    count = len(files_modified)
                    message = (
                        f"Would fix {count} file{'s' if count != 1 else ''}"
                    )
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message=message,
                        files_modified=files_modified,
                        file_modifications=file_modifications,
                    )

                # Configure git
                subprocess.run(
                    ["git", "config", "user.name", "pull-request-fixer"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [
                        "git",
                        "config",
                        "user.email",
                        "noreply@linuxfoundation.org",
                    ],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )

                # Stage the changes
                for file_path in files_modified:
                    rel_path = file_path.relative_to(repo_dir)
                    subprocess.run(
                        ["git", "add", str(rel_path)],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                    )

                # Check if there are actually changes to commit
                result = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    check=False,
                    cwd=repo_dir,
                    capture_output=True,
                )

                if result.returncode == 0:
                    # No changes - return early with success
                    self.logger.info("No formatting changes needed")
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message="Files were already properly formatted",
                        files_modified=[],
                        file_modifications=[],
                    )

                # Amend the last commit
                self.logger.debug("Amending last commit with file fixes")
                subprocess.run(
                    ["git", "commit", "--amend", "--no-edit"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Force push to update the PR
                self.logger.debug(f"Force pushing to {pr_info.head_ref}")
                try:
                    subprocess.run(
                        [
                            "git",
                            "push",
                            "--force-with-lease",
                            "origin",
                            pr_info.head_ref,
                        ],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    sanitized_stderr = self._sanitize_message(e.stderr or "")
                    self.logger.warning(
                        f"Push rejected - remote branch {pr_info.head_ref} was updated: {sanitized_stderr}"
                    )
                    error_msg = "Push rejected: PR branch was updated while processing. Please retry."
                    raise RuntimeError(error_msg) from e

                # Create a comment on the PR
                file_names = [
                    str(f.relative_to(repo_dir)) for f in files_modified
                ]
                comment_body = (
                    f"🛠️ **Pull Request Fixer**\n\n"
                    f"Fixed {total_changes} file(s): {', '.join(file_names)}\n\n"
                    f"The commit has been amended with the fixes.\n\n"
                    f"---\n"
                    f"*Automatically fixed by [pull-request-fixer]"
                    f"(https://github.com/lfit/pull-request-fixer)*"
                )

                with suppress(Exception):
                    await self.client.create_comment(
                        owner, repo, pr_info.number, comment_body
                    )

                count = len(files_modified)
                message = f"Updated {count} file{'s' if count != 1 else ''}"
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=True,
                    message=message,
                    files_modified=files_modified,
                    file_modifications=file_modifications,
                )

            except subprocess.CalledProcessError as e:
                # Sanitize all error output to prevent token exposure
                sanitized_stderr = self._sanitize_message(e.stderr or "")
                sanitized_stdout = self._sanitize_message(e.stdout or "")
                sanitized_error = self._sanitize_message(str(e))
                self.logger.error(
                    f"Git operation failed: {sanitized_stderr}",
                    extra={"stdout": sanitized_stdout},
                )
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=f"Git operation failed: {sanitized_stderr}",
                    error=sanitized_error,
                    file_modifications=[],
                )
            except RuntimeError as e:
                # Handle expected errors (push rejections)
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=str(e),
                    error=str(e),
                    file_modifications=[],
                )
            except Exception as e:
                # Sanitize exception messages to prevent token exposure
                sanitized_message = self._sanitize_message(str(e))
                self.logger.error(
                    f"Error during fix: {sanitized_message}", exc_info=True
                )
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=sanitized_message,
                    error=sanitized_message,
                    file_modifications=[],
                )
