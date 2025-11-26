#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Demo script for pull-request-fixer
# Shows the tool's capabilities for fixing PRs via GitHub integration

set -e

echo "🛠️  Pull Request Fixer Demo"
echo "============================"
echo ""

# Check if tool is installed
if ! command -v pull-request-fixer &> /dev/null; then
    echo "❌ pull-request-fixer is not installed"
    echo "   Install it with: pip install -e ."
    exit 1
fi

echo "✅ pull-request-fixer is installed"
echo ""

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable is not set"
    echo "   Set it with: export GITHUB_TOKEN=your_token_here"
    exit 1
fi

echo "✅ GITHUB_TOKEN is configured"
echo ""

echo "This tool can fix PR titles across GitHub organizations or individual PRs."
echo ""
echo "Usage examples:"
echo ""
echo "1. Fix a specific PR:"
echo "   pull-request-fixer https://github.com/owner/repo/pull/123"
echo ""
echo "2. Scan an organization (dry-run):"
echo "   pull-request-fixer ORG_NAME --dry-run"
echo ""
echo "3. Fix PRs across an organization:"
echo "   pull-request-fixer ORG_NAME"
echo ""
echo "For more information, run: pull-request-fixer --help"
echo ""
echo "Demo complete! 🎉"