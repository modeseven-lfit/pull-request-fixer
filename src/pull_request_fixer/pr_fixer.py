# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""PR fixer module.

Note: This module is kept for backwards compatibility but is not currently used.
The actual PR fixing logic is implemented directly in cli.py in the process_pr function.
All PR title and body fixing is handled there.

This module previously contained markdown table fixing code from the original
markdown-table-fixer tool, which has been removed as it's not relevant to this tool's purpose.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .github_client import GitHubClient


class PRFixer:
    """PR fixer class (currently unused).

    The actual PR fixing logic is implemented in cli.py.
    This class is kept for backwards compatibility.
    """

    def __init__(self, client: GitHubClient):
        """Initialize PR fixer.

        Args:
            client: GitHub API client
        """
        self.client = client
        self.logger = logging.getLogger("pull_request_fixer.pr_fixer")
