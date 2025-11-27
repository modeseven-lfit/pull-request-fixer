# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Comprehensive test suite for PR blocking detection.

Tests cover:
- Extracting failing checks from various check types
- Detecting blocked PRs with different blocking conditions
- Handling edge cases and malformed data
"""

from __future__ import annotations

from typing import Any

import pytest

from pull_request_fixer.github_client import GitHubClient
from pull_request_fixer.pr_scanner import PRScanner


class TestExtractFailingChecks:
    """Test suite for _extract_failing_checks method."""

    @pytest.fixture
    def scanner(self) -> PRScanner:
        """Create a PRScanner instance for testing."""
        client = GitHubClient(token="test-token")
        return PRScanner(client)

    def test_no_commits(self, scanner: PRScanner) -> None:
        """Test when PR has no commits."""
        pr_data = {"commits": None}
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []

    def test_empty_commits(self, scanner: PRScanner) -> None:
        """Test when commits list is empty."""
        pr_data: dict[str, Any] = {"commits": {"nodes": []}}
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []

    def test_no_status_check_rollup(self, scanner: PRScanner) -> None:
        """Test when commit has no statusCheckRollup."""
        pr_data = {
            "commits": {"nodes": [{"commit": {"statusCheckRollup": None}}]}
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []

    def test_check_run_failure(self, scanner: PRScanner) -> None:
        """Test detecting failed CheckRun."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "CI Tests",
                                            "conclusion": "failure",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["CI Tests"]

    def test_check_run_cancelled(self, scanner: PRScanner) -> None:
        """Test detecting cancelled CheckRun."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Build",
                                            "conclusion": "cancelled",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["Build"]

    def test_check_run_timed_out(self, scanner: PRScanner) -> None:
        """Test detecting timed out CheckRun."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Slow Test",
                                            "conclusion": "timed_out",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["Slow Test"]

    def test_check_run_action_required(self, scanner: PRScanner) -> None:
        """Test detecting CheckRun requiring action."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Manual Approval",
                                            "conclusion": "action_required",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["Manual Approval"]

    def test_check_run_success(self, scanner: PRScanner) -> None:
        """Test that successful CheckRun is not reported as failing."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Passing Test",
                                            "conclusion": "success",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []

    def test_status_context_failure(self, scanner: PRScanner) -> None:
        """Test detecting failed StatusContext."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "StatusContext",
                                            "context": "continuous-integration/jenkins",
                                            "state": "FAILURE",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["continuous-integration/jenkins"]

    def test_status_context_error(self, scanner: PRScanner) -> None:
        """Test detecting errored StatusContext."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "StatusContext",
                                            "context": "security/scan",
                                            "state": "ERROR",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["security/scan"]

    def test_status_context_success(self, scanner: PRScanner) -> None:
        """Test that successful StatusContext is not reported as failing."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "StatusContext",
                                            "context": "ci/test",
                                            "state": "SUCCESS",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []

    def test_multiple_failing_checks(self, scanner: PRScanner) -> None:
        """Test detecting multiple failing checks."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test Suite",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "StatusContext",
                                            "context": "ci/build",
                                            "state": "FAILURE",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Lint",
                                            "conclusion": "cancelled",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert len(failing) == 3
        assert "Test Suite" in failing
        assert "ci/build" in failing
        assert "Lint" in failing

    def test_mixed_passing_and_failing_checks(self, scanner: PRScanner) -> None:
        """Test with mix of passing and failing checks."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Passing Test",
                                            "conclusion": "success",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Failing Test",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "StatusContext",
                                            "context": "ci/passing",
                                            "state": "SUCCESS",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == ["Failing Test"]

    def test_check_without_name(self, scanner: PRScanner) -> None:
        """Test handling check without name field."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "conclusion": "failure",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []  # Check without name should be skipped

    def test_status_without_context(self, scanner: PRScanner) -> None:
        """Test handling StatusContext without context field."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "StatusContext",
                                            "state": "FAILURE",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []  # Status without context should be skipped

    def test_unknown_check_type(self, scanner: PRScanner) -> None:
        """Test handling unknown check type."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "UnknownCheckType",
                                            "name": "Some Check",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert failing == []  # Unknown type should be ignored

    def test_case_insensitive_conclusion(self, scanner: PRScanner) -> None:
        """Test that conclusion check is case-insensitive."""
        pr_data = {
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test 1",
                                            "conclusion": "FAILURE",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test 2",
                                            "conclusion": "Failure",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test 3",
                                            "conclusion": "failure",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
        failing = scanner._extract_failing_checks(pr_data)
        assert len(failing) == 3


class TestIsPRBlocked:
    """Test suite for is_pr_blocked method."""

    @pytest.fixture
    def scanner(self) -> PRScanner:
        """Create a PRScanner instance for testing."""
        client = GitHubClient(token="test-token")
        return PRScanner(client)

    def test_not_blocked(self, scanner: PRScanner) -> None:
        """Test PR that is not blocked."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_blocked_by_conflicts(self, scanner: PRScanner) -> None:
        """Test PR blocked by merge conflicts."""
        pr_data = {
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "CLEAN",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert "Merge conflicts" in reasons

    def test_blocked_by_failing_checks(self, scanner: PRScanner) -> None:
        """Test PR blocked by failing checks."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "CI Test",
                                            "conclusion": "failure",
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            },
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert any("Failing checks: CI Test" in r for r in reasons)

    def test_blocked_by_branch_protection(self, scanner: PRScanner) -> None:
        """Test PR blocked by branch protection rules."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BLOCKED",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert "Blocked by branch protection rules" in reasons

    def test_behind_base_branch(self, scanner: PRScanner) -> None:
        """Test PR that is behind base branch."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BEHIND",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert "Behind base branch" in reasons

    def test_multiple_blocking_reasons(self, scanner: PRScanner) -> None:
        """Test PR blocked by multiple reasons."""
        pr_data = {
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "BLOCKED",
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test 1",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test 2",
                                            "conclusion": "failure",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            },
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert len(reasons) == 3
        assert "Merge conflicts" in reasons
        assert any("Failing checks:" in r for r in reasons)
        assert "Blocked by branch protection rules" in reasons

    def test_unknown_mergeable_state(self, scanner: PRScanner) -> None:
        """Test PR with unknown mergeable state."""
        pr_data = {
            "mergeable": "UNKNOWN",
            "mergeStateStatus": "CLEAN",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_missing_mergeable_field(self, scanner: PRScanner) -> None:
        """Test PR data without mergeable field."""
        pr_data = {
            "mergeStateStatus": "CLEAN",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_missing_merge_state_status(self, scanner: PRScanner) -> None:
        """Test PR data without mergeStateStatus field."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_multiple_failing_checks_grouped(self, scanner: PRScanner) -> None:
        """Test that multiple failing checks are grouped in one reason."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test A",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Test B",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "StatusContext",
                                            "context": "ci/test",
                                            "state": "FAILURE",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            },
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert len(reasons) == 1  # All checks grouped in one reason
        reason = reasons[0]
        assert "Failing checks:" in reason
        assert "Test A" in reason
        assert "Test B" in reason
        assert "ci/test" in reason

    def test_empty_pr_data(self, scanner: PRScanner) -> None:
        """Test handling of empty PR data."""
        pr_data: dict[str, Any] = {}
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_draft_pr_not_automatically_blocked(
        self, scanner: PRScanner
    ) -> None:
        """Test that draft status alone doesn't block PR."""
        pr_data = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "isDraft": True,
            "commits": {"nodes": []},
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert not is_blocked
        assert reasons == []

    def test_blocked_reasons_formatting(self, scanner: PRScanner) -> None:
        """Test that blocking reasons are properly formatted."""
        pr_data = {
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "BLOCKED",
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {
                                    "nodes": [
                                        {
                                            "__typename": "CheckRun",
                                            "name": "Semantic Pull Request",
                                            "conclusion": "failure",
                                        },
                                        {
                                            "__typename": "CheckRun",
                                            "name": "pre-commit.ci - pr",
                                            "conclusion": "failure",
                                        },
                                    ]
                                }
                            }
                        }
                    }
                ]
            },
        }
        is_blocked, reasons = scanner.is_pr_blocked(pr_data)
        assert is_blocked
        assert len(reasons) == 3

        # Check that failing checks are comma-separated
        checks_reason = [r for r in reasons if "Failing checks:" in r][0]
        assert "Semantic Pull Request" in checks_reason
        assert "pre-commit.ci - pr" in checks_reason
        assert ", " in checks_reason  # Check names are comma-separated
