#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Debug script to test GraphQL queries against the real GitHub API.

This script helps diagnose issues with GraphQL queries by:
1. Testing authentication
2. Validating query syntax
3. Showing actual API responses
4. Testing parameter handling

Usage:
    python scripts/debug_graphql.py --org myorg --token $GITHUB_TOKEN
    python scripts/debug_graphql.py --org myorg --repo myrepo --pr 123
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pull_request_fixer.github_client import GitHubClient
from pull_request_fixer.graphql_queries import (
    ORG_REPOS_ONLY,
    ORG_REPOS_WITH_PRS,
    PR_FIRST_COMMIT,
    REPO_OPEN_PRS_PAGE,
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_json(data: Any, title: str = "Response") -> None:
    """Pretty print JSON data."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print("=" * 80)
    print(json.dumps(data, indent=2, sort_keys=True))
    print("=" * 80 + "\n")


async def test_authentication(client: GitHubClient) -> bool:
    """Test authentication with a simple query."""
    print("\n🔐 Testing authentication...")

    try:
        query = """
        query {
          viewer {
            login
            name
          }
        }
        """
        result = await client.graphql(query)

        if "viewer" in result:
            print("✅ Authentication successful!")
            print(f"   Authenticated as: {result['viewer']['login']}")
            if result["viewer"].get("name"):
                print(f"   Name: {result['viewer']['name']}")
            return True
        else:
            print("❌ Authentication failed - no viewer data")
            print_json(result, "Response")
            return False

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        logger.exception("Authentication error")
        return False


async def test_org_repos_only(client: GitHubClient, org: str) -> None:
    """Test ORG_REPOS_ONLY query."""
    print(f"\n📚 Testing ORG_REPOS_ONLY query for '{org}'...")

    try:
        variables = {"org": org, "reposCursor": None}

        print(f"Variables: {json.dumps(variables, indent=2)}")
        result = await client.graphql(ORG_REPOS_ONLY, variables=variables)

        if "organization" in result:
            org_data = result["organization"]
            if org_data:
                repos = org_data.get("repositories", {})
                total = repos.get("totalCount", 0)
                nodes = repos.get("nodes", [])

                print("✅ Query successful!")
                print(f"   Total repositories: {total}")
                print(f"   Returned in this page: {len(nodes)}")

                if nodes:
                    print("   Sample repositories:")
                    for repo in nodes[:5]:
                        archived = (
                            " (archived)" if repo.get("isArchived") else ""
                        )
                        print(f"     - {repo['nameWithOwner']}{archived}")

                print_json(result, f"Full Response for {org}")
            else:
                print("❌ Organization data is null")
                print_json(result, "Response")
        else:
            print("❌ No 'organization' key in response")
            print_json(result, "Response")

    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.exception("ORG_REPOS_ONLY error")


async def test_org_repos_with_prs(client: GitHubClient, org: str) -> None:
    """Test ORG_REPOS_WITH_PRS query."""
    print(f"\n📋 Testing ORG_REPOS_WITH_PRS query for '{org}'...")

    try:
        variables = {
            "org": org,
            "cursor": None,
            "prsPageSize": 1,
            "contextsPageSize": 0,
        }

        print(f"Variables: {json.dumps(variables, indent=2)}")
        result = await client.graphql(ORG_REPOS_WITH_PRS, variables=variables)

        if "organization" in result and result["organization"]:
            org_data = result["organization"]
            repos = org_data.get("repositories", {})
            nodes = repos.get("nodes", [])

            print("✅ Query successful!")
            print(f"   Repositories with PRs in this page: {len(nodes)}")

            for repo in nodes:
                pr_count = repo.get("pullRequests", {}).get("totalCount", 0)
                print(f"     - {repo['nameWithOwner']}: {pr_count} open PRs")

            print_json(result, f"Full Response for {org}")
        else:
            print("❌ No organization data")
            print_json(result, "Response")

    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.exception("ORG_REPOS_WITH_PRS error")


async def test_repo_open_prs(
    client: GitHubClient, owner: str, repo: str
) -> None:
    """Test REPO_OPEN_PRS_PAGE query."""
    print(f"\n📝 Testing REPO_OPEN_PRS_PAGE query for '{owner}/{repo}'...")

    try:
        variables = {
            "owner": owner,
            "name": repo,
            "prsCursor": None,
            "prsPageSize": 10,
            "filesPageSize": 10,
            "commentsPageSize": 5,
            "contextsPageSize": 10,
        }

        print(f"Variables: {json.dumps(variables, indent=2)}")
        result = await client.graphql(REPO_OPEN_PRS_PAGE, variables=variables)

        if "repository" in result and result["repository"]:
            repo_data = result["repository"]
            prs = repo_data.get("pullRequests", {})
            nodes = prs.get("nodes", [])

            print("✅ Query successful!")
            print(f"   Open PRs: {len(nodes)}")

            for pr in nodes:
                draft = " (draft)" if pr.get("isDraft") else ""
                print(f"     - PR #{pr['number']}: {pr['title']}{draft}")

            print_json(result, f"Full Response for {owner}/{repo}")
        else:
            print("❌ No repository data")
            print_json(result, "Response")

    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.exception("REPO_OPEN_PRS_PAGE error")


async def test_pr_first_commit(
    client: GitHubClient, owner: str, repo: str, pr_num: int
) -> None:
    """Test PR_FIRST_COMMIT query."""
    print(
        f"\n💬 Testing PR_FIRST_COMMIT query for '{owner}/{repo}#{pr_num}'..."
    )

    try:
        variables = {"owner": owner, "name": repo, "number": pr_num}

        print(f"Variables: {json.dumps(variables, indent=2)}")
        result = await client.graphql(PR_FIRST_COMMIT, variables=variables)

        if "repository" in result and result["repository"]:
            repo_data = result["repository"]
            pr_data = repo_data.get("pullRequest")

            if pr_data:
                print("✅ Query successful!")
                print(f"   PR #{pr_data['number']}: {pr_data['title']}")

                commits = pr_data.get("commits", {}).get("nodes", [])
                if commits:
                    commit = commits[0].get("commit", {})
                    msg = commit.get("message", "")
                    headline = commit.get("messageHeadline", "")

                    print(f"   First commit headline: {headline}")
                    print(f"   Full message preview: {msg[:100]}...")

                    # Check if title matches
                    if pr_data["title"] == headline:
                        print("   ✅ Title matches first commit!")
                    else:
                        print("   ⚠️  Title DOES NOT match first commit")
                        print(f"      PR Title:     {pr_data['title']}")
                        print(f"      Commit Title: {headline}")
                else:
                    print("   ⚠️  No commits found")

                print_json(result, f"Full Response for PR #{pr_num}")
            else:
                print("❌ PR not found")
                print_json(result, "Response")
        else:
            print("❌ No repository data")
            print_json(result, "Response")

    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.exception("PR_FIRST_COMMIT error")


async def test_rate_limit(client: GitHubClient) -> None:
    """Test rate limit endpoint."""
    print("\n⏱️  Checking rate limit...")

    try:
        result = await client.get_rate_limit()

        if "resources" in result:
            graphql = result["resources"].get("graphql", {})
            core = result["resources"].get("core", {})

            print("✅ Rate limit info:")
            print("   GraphQL:")
            print(
                f"     Remaining: {graphql.get('remaining')}/{graphql.get('limit')}"
            )
            print(f"     Resets at: {graphql.get('reset')}")
            print("   Core API:")
            print(
                f"     Remaining: {core.get('remaining')}/{core.get('limit')}"
            )
            print(f"     Resets at: {core.get('reset')}")
        else:
            print_json(result, "Rate Limit Response")

    except Exception as e:
        print(f"❌ Failed to get rate limit: {e}")
        logger.exception("Rate limit error")


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Debug GraphQL queries against GitHub API"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument("--org", help="Organization name to test")
    parser.add_argument("--repo", help="Repository name (requires --org)")
    parser.add_argument(
        "--pr", type=int, help="PR number to test (requires --org and --repo)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all tests (org level only)"
    )

    args = parser.parse_args()

    if not args.token:
        print("❌ Error: No GitHub token provided")
        print("   Set GITHUB_TOKEN env var or use --token")
        sys.exit(1)

    print("=" * 80)
    print("  GraphQL Debug Tool")
    print("=" * 80)

    async with GitHubClient(args.token) as client:
        # Always test auth first
        if not await test_authentication(client):
            print("\n❌ Authentication failed. Please check your token.")
            sys.exit(1)

        # Check rate limit
        await test_rate_limit(client)

        # Test based on arguments
        if args.org:
            # Test org-level queries
            await test_org_repos_only(client, args.org)

            if args.all or not args.repo:
                await test_org_repos_with_prs(client, args.org)

            # Test repo-level queries
            if args.repo:
                await test_repo_open_prs(client, args.org, args.repo)

                # Test PR-level queries
                if args.pr:
                    await test_pr_first_commit(
                        client, args.org, args.repo, args.pr
                    )
        else:
            print("\n💡 Tip: Use --org to test organization queries")
            print("   Example: python scripts/debug_graphql.py --org myorg")
            print(
                "   Example: python scripts/debug_graphql.py --org myorg --repo myrepo"
            )
            print(
                "   Example: python scripts/debug_graphql.py --org myorg --repo myrepo --pr 123"
            )

    print("\n✅ Debug session complete!")


if __name__ == "__main__":
    asyncio.run(main())
