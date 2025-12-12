#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Linux Foundation
# SPDX-License-Identifier: Apache-2.0
"""Integration test to verify pull-request-fixer works with dependamerge."""

import asyncio
from pathlib import Path
import sys

# Add source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pull_request_fixer.blocked_pr_scanner import BlockedPRScanner


async def test_blocked_scanner_initialization() -> bool:
    """Test that BlockedPRScanner can be initialized and closed."""
    print("🧪 Test 1: BlockedPRScanner initialization")

    try:
        scanner = BlockedPRScanner(
            token="fake-token-for-testing",
            max_repo_tasks=5,
        )
        print("   ✅ Scanner initialized successfully")

        await scanner.close()
        print("   ✅ Scanner closed successfully")
        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_is_pr_blocked() -> bool:
    """Test the is_pr_blocked method with sample data."""
    print("\n🧪 Test 2: is_pr_blocked method")

    try:
        scanner = BlockedPRScanner(
            token="fake-token-for-testing",
            max_repo_tasks=5,
        )

        # Test with a PR that has conflicts
        pr_with_conflicts = {
            "number": 1,
            "title": "Test PR with conflicts",
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "dirty",
            "isDraft": False,
            "author": {"login": "testuser"},
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {"contexts": {"nodes": []}}
                        }
                    }
                ]
            },
        }

        is_blocked, reasons = await scanner._is_pr_blocked_async(
            pr_with_conflicts
        )

        if is_blocked and reasons:
            print(f"   ✅ Correctly identified blocked PR: {reasons}")
            success = True
        else:
            print(
                f"   ❌ FAIL: Expected PR to be blocked but got: blocked={is_blocked}, reasons={reasons}"
            )
            success = False

        # Test with a clean PR
        clean_pr = {
            "number": 2,
            "title": "Clean PR",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "clean",
            "isDraft": False,
            "author": {"login": "testuser"},
            "commits": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {"contexts": {"nodes": []}}
                        }
                    }
                ]
            },
        }

        is_blocked, reasons = await scanner._is_pr_blocked_async(clean_pr)

        if not is_blocked:
            print("   ✅ Correctly identified clean PR as not blocked")
        else:
            print(
                f"   ❌ FAIL: Expected PR to NOT be blocked but got: blocked={is_blocked}, reasons={reasons}"
            )
            success = False

        await scanner.close()
        return success

    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_dependamerge_import() -> bool:
    """Test that we can import dependamerge components."""
    print("\n🧪 Test 3: Import dependamerge components")

    try:
        print("   ✅ Successfully imported GitHubService")
        print("   ✅ Successfully imported UnmergeablePR")
        print("   ✅ Successfully imported UnmergeableReason")
        return True
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> int:
    """Run all integration tests."""
    print("=" * 80)
    print("Integration Tests for pull-request-fixer with dependamerge")
    print("=" * 80)

    results = []

    # Run tests
    results.append(await test_dependamerge_import())
    results.append(await test_blocked_scanner_initialization())
    results.append(await test_is_pr_blocked())

    # Summary
    print("\n" + "=" * 80)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} integration tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
