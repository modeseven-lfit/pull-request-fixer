# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Test suite for PRFileFixer 404 error handling.

Tests that 404 errors (PR not found) are handled gracefully without
showing ugly stack traces to users.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from pull_request_fixer.exceptions import ResourceNotFoundError
from pull_request_fixer.github_client import GitHubClient
from pull_request_fixer.pr_file_fixer import PRFileFixer


class TestPRNotFoundHandling:
    """Test suite for handling 404 errors when PR doesn't exist."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create a mock GitHub client."""
        client = Mock(spec=GitHubClient)
        client.token = "test_token"
        client._request = AsyncMock()
        client.get_pr_files = AsyncMock()
        client.get_file_content = AsyncMock()
        client.update_files_in_batch = AsyncMock()
        client.create_comment = AsyncMock()
        return client

    @pytest.fixture
    def pr_fixer(self, mock_client: Mock) -> PRFileFixer:
        """Create PRFileFixer with mock client."""
        return PRFileFixer(mock_client)

    @pytest.mark.asyncio
    async def test_pr_not_found_returns_friendly_error(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
    ) -> None:
        """Test that 404 error returns friendly message without stack trace."""
        # Setup - API returns 404 (ResourceNotFoundError)
        mock_client._request.side_effect = ResourceNotFoundError(
            'Resource not found: {"message":"Not Found"}'
        )

        # Execute - try to fix a non-existent PR
        result = await pr_fixer.fix_pr_by_url(
            pr_url="https://github.com/owner/repo/pull/999",
            file_pattern=r"\.yaml$",
            search_pattern=r"old_value",
            replacement="new_value",
            dry_run=False,
        )

        # Verify - should return friendly error message
        assert result.success is False
        assert "not found" in result.message.lower()
        assert "Pull request #999" in result.message
        assert (
            "closed, merged, or deleted" in result.message
            or "not found" in result.message.lower()
        )

        # Verify PR info is still populated with what we know
        assert result.pr_info.number == 999
        assert result.pr_info.repository == "owner/repo"
        assert result.pr_info.url == "https://github.com/owner/repo/pull/999"

    @pytest.mark.asyncio
    async def test_other_errors_still_propagate(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
    ) -> None:
        """Test that non-404 errors still propagate normally."""
        # Setup - API returns a different error (e.g., 403 Forbidden)
        mock_client._request.side_effect = Exception("API Error: 403 Forbidden")

        # Execute and verify - should raise the exception
        result = await pr_fixer.fix_pr_by_url(
            pr_url="https://github.com/owner/repo/pull/123",
            file_pattern=r"\.yaml$",
            search_pattern=r"old_value",
            replacement="new_value",
            dry_run=False,
        )

        # Should return error result
        assert result.success is False
        assert "API Error: 403 Forbidden" in result.message

    @pytest.mark.asyncio
    async def test_invalid_pr_url_format(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
    ) -> None:
        """Test that invalid PR URL format returns friendly error."""
        # Execute - try with invalid URL
        result = await pr_fixer.fix_pr_by_url(
            pr_url="https://github.com/invalid",
            file_pattern=r"\.yaml$",
            search_pattern=r"old_value",
            replacement="new_value",
            dry_run=False,
        )

        # Verify
        assert result.success is False
        assert "Invalid PR URL format" in result.message
        assert result.pr_info.number == 0
