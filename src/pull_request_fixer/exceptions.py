# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Custom exceptions for pr-title-fixer."""

from __future__ import annotations


class PRTitleFixerError(Exception):
    """Base exception for pr-title-fixer."""

    pass


class FileAccessError(PRTitleFixerError):
    """Error accessing or reading a file."""

    pass


class ResourceNotFoundError(PRTitleFixerError):
    """Resource not found (404 error)."""

    pass


class GitHubAPIError(PRTitleFixerError):
    """Error communicating with GitHub API."""

    pass


class AuthenticationError(GitHubAPIError):
    """GitHub authentication failed."""

    pass


class RateLimitError(GitHubAPIError):
    """GitHub API rate limit exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: int | None = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            reset_time: Unix timestamp when rate limit resets
        """
        super().__init__(message)
        self.reset_time = reset_time


class NetworkError(PRTitleFixerError):
    """Network communication error."""

    pass


class GitOperationError(PRTitleFixerError):
    """Error performing git operation."""

    pass


class ConfigurationError(PRTitleFixerError):
    """Configuration error."""

    pass
