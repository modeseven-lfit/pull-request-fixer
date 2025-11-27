# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Data models for pr-title-fixer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class OutputFormat(str, Enum):
    """Output format options."""

    TEXT = "text"
    JSON = "json"
    TABLE = "table"


@dataclass
class PRInfo:
    """Information about a GitHub pull request."""

    number: int
    title: str
    repository: str
    url: str
    author: str
    is_draft: bool
    head_ref: str
    head_sha: str
    base_ref: str
    mergeable: str
    merge_state_status: str


@dataclass
class BlockedPR:
    """A blocked pull request with blocking reasons."""

    pr_info: PRInfo
    blocking_reasons: list[str]
    has_title_issues: bool = False


@dataclass
class GitHubScanResult:
    """Results from scanning a GitHub organization."""

    organization: str
    repositories_scanned: int = 0
    total_prs: int = 0
    blocked_prs: list[BlockedPR] = field(default_factory=list)
    prs_fixed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class GitHubFixResult:
    """Result of fixing a PR."""

    pr_info: PRInfo
    success: bool
    message: str
    files_modified: list[Path] = field(default_factory=list)
    error: str | None = None
