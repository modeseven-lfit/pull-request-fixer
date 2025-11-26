# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Command-line interface for pull-request-fixer."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
import typer

from ._version import __version__
from .github_client import GitHubClient
from .models import PRInfo
from .pr_fixer import PRFixer
from .pr_scanner import PRScanner
from .progress_tracker import ProgressTracker

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"🏷️  pull-request-fixer version {__version__}")
        console.print()
        raise typer.Exit()


def setup_logging(
    log_level: str = "INFO", quiet: bool = False, verbose: bool = False
) -> None:
    """Configure logging with Rich handler."""
    if quiet:
        log_level = "ERROR"
    elif verbose:
        log_level = "DEBUG"

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[
            RichHandler(console=console, show_time=False, show_path=False)
        ],
    )

    # Silence httpx INFO logs to prevent Rich display interruption
    logging.getLogger("httpx").setLevel(logging.WARNING)


def parse_target(target: str) -> tuple[str, str | None]:
    """Parse target to determine if it's an organization or a specific PR URL.
    
    Args:
        target: Organization name, GitHub URL, or PR URL
        
    Returns:
        Tuple of (type, value) where:
        - type is "org" or "pr"
        - value is organization name for "org", or PR URL for "pr"
        
    Examples:
        parse_target("myorg") -> ("org", "myorg")
        parse_target("https://github.com/myorg") -> ("org", "myorg")
        parse_target("https://github.com/owner/repo/pull/123") -> ("pr", "https://github.com/owner/repo/pull/123")
    """
    # Remove trailing slash
    target = target.rstrip("/")
    
    # Check if it's a PR URL
    if "/pull/" in target or "/pulls/" in target:
        # It's a specific PR URL
        return ("pr", target)
    
    # Check if it's a GitHub URL
    if "github.com" in target:
        # Extract org from URL: https://github.com/ORG or https://github.com/ORG/...
        parts = target.split("github.com/")
        if len(parts) > 1:
            # Get the part after github.com/
            path = parts[1]
            # Split by / and take first part (the org)
            org = path.split("/")[0]
            return ("org", org)
    
    # Not a URL, return as organization
    return ("org", target)


def extract_pr_info_from_url(pr_url: str) -> tuple[str, str, int] | None:
    """Extract owner, repo, and PR number from a PR URL.
    
    Args:
        pr_url: GitHub PR URL
        
    Returns:
        Tuple of (owner, repo, pr_number) or None if invalid
        
    Example:
        extract_pr_info_from_url("https://github.com/owner/repo/pull/123") 
        -> ("owner", "repo", 123)
    """
    # Match pattern: https://github.com/OWNER/REPO/pull(s)/NUMBER
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/pulls?/(\d+)",
        pr_url
    )
    if match:
        owner = match.group(1)
        repo = match.group(2)
        pr_number = int(match.group(3))
        return (owner, repo, pr_number)
    return None


# Create Typer app
app = typer.Typer(
    name="pull-request-fixer",
    help="Fix pull requests with GitHub integration",
    add_completion=False,
    rich_markup_mode="rich",
)


def main(
    target: str = typer.Argument(
        None,
        help="GitHub organization name/URL or PR URL (e.g., 'myorg', 'https://github.com/myorg', or 'https://github.com/owner/repo/pull/123')",
    ),
    token: str | None = typer.Option(
        None,
        "--token",
        "-t",
        help="GitHub token (or set GITHUB_TOKEN env var)",
        envvar="GITHUB_TOKEN",
    ),
    fix_title: bool = typer.Option(
        False,
        "--fix-title",
        help="Fix PR title to match first commit message subject",
    ),
    fix_body: bool = typer.Option(
        False,
        "--fix-body",
        help="Fix PR body to match first commit message body (excluding trailers)",
    ),
    include_drafts: bool = typer.Option(
        False,
        "--include-drafts",
        help="Include draft PRs in scan",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without applying them",
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-j",
        min=1,
        max=32,
        help="Number of parallel workers (default: 4)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress all output except errors",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Set logging level",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """
    Pull request fixer - automatically fix PR titles and bodies from commit messages.

    Can process either:
    - An entire organization: Scans for all blocked pull requests
    - A specific PR: Processes only that pull request

    Examples:
      pull-request-fixer myorg --fix-title --fix-body
      pull-request-fixer https://github.com/myorg --fix-title --dry-run
      pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title
      pull-request-fixer myorg --fix-title --workers 8 --verbose
    """
    # If no target provided, show help
    if target is None:
        console.print("Error: Missing required argument 'TARGET'.")
        console.print()
        console.print("Usage: pull-request-fixer [OPTIONS] TARGET")
        console.print()
        console.print("TARGET can be:")
        console.print("  - Organization name: myorg")
        console.print("  - Organization URL: https://github.com/myorg")
        console.print("  - Specific PR URL: https://github.com/owner/repo/pull/123")
        console.print()
        console.print("Run 'pull-request-fixer --help' for more information.")
        raise typer.Exit(1)

    setup_logging(log_level=log_level, quiet=quiet, verbose=verbose)

    # Validate that at least one fix option is enabled
    if not fix_title and not fix_body:
        console.print(
            "[yellow]Warning:[/yellow] No fix options specified. "
            "Use --fix-title and/or --fix-body to enable fixes."
        )
        console.print()
        console.print("Available options:")
        console.print("  --fix-title  Fix PR title to match first commit subject")
        console.print("  --fix-body   Fix PR body to match first commit body")
        console.print()
        console.print("Example: pull-request-fixer myorg --fix-title --fix-body")
        raise typer.Exit(1)

    if not token:
        console.print(
            "[red]Error:[/red] GitHub token required. "
            "Provide --token or set GITHUB_TOKEN environment variable"
        )
        raise typer.Exit(1)

    # Parse target to determine if it's an org or a specific PR
    target_type, target_value = parse_target(target)

    if target_type == "pr":
        # Process single PR
        asyncio.run(
            process_single_pr(
                pr_url=target_value,
                token=token,
                fix_title=fix_title,
                fix_body=fix_body,
                dry_run=dry_run,
                quiet=quiet,
            )
        )
    else:
        # Scan organization
        asyncio.run(
            scan_and_fix_organization(
                org=target_value,
                token=token,
                fix_title=fix_title,
                fix_body=fix_body,
                include_drafts=include_drafts,
                dry_run=dry_run,
                workers=workers,
                quiet=quiet,
            )
        )


async def process_single_pr(
    pr_url: str,
    token: str,
    fix_title: bool,
    fix_body: bool,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Process a single PR by URL.
    
    Args:
        pr_url: GitHub PR URL
        token: GitHub token
        fix_title: Whether to fix PR title
        fix_body: Whether to fix PR body
        dry_run: Whether to preview without applying changes
        quiet: Whether to suppress output
    """
    if not quiet:
        console.print(f"🔍 Processing PR: {pr_url}")
        fixes = []
        if fix_title:
            fixes.append("title")
        if fix_body:
            fixes.append("body")
        console.print(f"🔧 Will fix: {', '.join(fixes)}")
        if dry_run:
            console.print("🏃 Dry run mode: no changes will be applied")
        console.print()

    # Extract PR info from URL
    pr_info = extract_pr_info_from_url(pr_url)
    if not pr_info:
        console.print(f"[red]Error:[/red] Invalid PR URL: {pr_url}")
        console.print()
        console.print("Expected format: https://github.com/owner/repo/pull/123")
        raise typer.Exit(1)
    
    owner, repo_name, pr_number = pr_info

    try:
        async with GitHubClient(token) as client:  # type: ignore[attr-defined]
            # Fetch PR data
            if not quiet:
                console.print(f"📥 Fetching PR data...")
            
            endpoint = f"/repos/{owner}/{repo_name}/pulls/{pr_number}"
            pr_data = await client._request("GET", endpoint)
            
            if not pr_data:
                console.print(f"[red]Error:[/red] Could not fetch PR data")
                raise typer.Exit(1)
            
            # Process the PR
            semaphore = asyncio.Semaphore(1)  # Single PR, no parallelism needed
            result = await process_pr(
                client=client,
                fixer=None,  # Not needed for single PR
                owner=owner,
                repo_name=repo_name,
                pr_data=pr_data,
                fix_title=fix_title,
                fix_body=fix_body,
                dry_run=dry_run,
                quiet=quiet,
                semaphore=semaphore,
            )
            
            if not quiet:
                console.print()
                if result:
                    if dry_run:
                        console.print("[green]✅ [DRY RUN] Would fix this PR[/green]")
                    else:
                        console.print("[green]✅ PR updated successfully[/green]")
                else:
                    console.print("[yellow]ℹ️  No changes needed or applied[/yellow]")

    except Exception as e:
        console.print(f"[red]Error processing PR:[/red] {e}")
        if not quiet:
            import traceback
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        raise typer.Exit(1) from e


async def scan_and_fix_organization(
    org: str,
    token: str,
    fix_title: bool,
    fix_body: bool,
    include_drafts: bool,
    dry_run: bool,
    workers: int,
    quiet: bool,
) -> None:
    """Scan organization for blocked PRs and fix them.
    
    Args:
        org: Organization name
        token: GitHub token
        fix_title: Whether to fix PR titles
        fix_body: Whether to fix PR bodies
        include_drafts: Whether to include draft PRs
        dry_run: Whether to preview without applying changes
        workers: Number of parallel workers
        quiet: Whether to suppress output
    """
    if not quiet:
        console.print(f"🔍 Scanning organization: {org}")
        fixes = []
        if fix_title:
            fixes.append("titles")
        if fix_body:
            fixes.append("bodies")
        console.print(f"🔧 Will fix: {', '.join(fixes)}")
        if dry_run:
            console.print("🏃 Dry run mode: no changes will be applied")
        console.print()

    try:
        async with GitHubClient(token) as client:  # type: ignore[attr-defined]
            # Create progress tracker for visual feedback
            progress_tracker = (
                None if quiet else ProgressTracker(org, show_pr_stats=True)
            )

            scanner = PRScanner(
                client, 
                progress_tracker=progress_tracker,
                max_repo_tasks=workers,
                max_page_tasks=workers * 2,
            )
            fixer = PRFixer(client)

            # Collect blocked PRs
            blocked_prs: list[tuple[str, str, dict]] = []

            if progress_tracker:
                progress_tracker.start()

            try:
                async for owner, repo_name, pr_data in scanner.scan_organization(
                    org, include_drafts=include_drafts
                ):
                    # Store blocked PR info
                    blocked_prs.append((owner, repo_name, pr_data))

            except Exception as scan_error:
                if progress_tracker:
                    progress_tracker.stop()
                console.print(
                    f"\n[yellow]⚠️  Scanning interrupted: {scan_error}[/yellow]"
                )
                console.print("[yellow]Processing PRs found so far...[/yellow]")

            # Stop progress tracker
            if progress_tracker:
                progress_tracker.stop()

            if not quiet:
                console.print(
                    f"\n📊 Found {len(blocked_prs)} blocked PRs to process"
                )

            if not blocked_prs:
                console.print(
                    "\n[green]✅ No blocked PRs found![/green]"
                )
                return

            # Display found PRs
            if not quiet:
                console.print("\n🔍 Blocked PRs:")
                for owner, repo_name, pr_data in blocked_prs:
                    pr_num = pr_data.get("number", "?")
                    pr_title = pr_data.get("title", "")
                    console.print(f"   • {owner}/{repo_name}#{pr_num}: {pr_title}")

            if not quiet:
                if dry_run:
                    console.print(
                        f"\n🔍 [DRY RUN] Analyzing {len(blocked_prs)} PRs..."
                    )
                else:
                    console.print(f"\n🔧 Processing {len(blocked_prs)} PRs...")

            # Process PRs in parallel using semaphore for concurrency control
            semaphore = asyncio.Semaphore(workers)
            tasks = []
            
            for owner, repo_name, pr_data in blocked_prs:
                task = process_pr(
                    client=client,
                    fixer=fixer,
                    owner=owner,
                    repo_name=repo_name,
                    pr_data=pr_data,
                    fix_title=fix_title,
                    fix_body=fix_body,
                    dry_run=dry_run,
                    quiet=quiet,
                    semaphore=semaphore,
                )
                tasks.append(asyncio.create_task(task))

            # Wait for all processing to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            fixed_count = 0
            error_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                elif result:
                    fixed_count += 1

            # Summary
            if not quiet:
                console.print()
                if dry_run:
                    console.print(
                        f"[green]✅ [DRY RUN] Would fix {fixed_count} PR(s)[/green]"
                    )
                else:
                    console.print(
                        f"[green]✅ Fixed {fixed_count} PR(s)[/green]"
                    )
                if error_count > 0:
                    console.print(
                        f"[yellow]⚠️  {error_count} error(s) encountered[/yellow]"
                    )

    except Exception as e:
        console.print(f"[red]Error scanning organization:[/red] {e}")
        if not quiet:
            import traceback
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        raise typer.Exit(1) from e


async def process_pr(
    client: GitHubClient,
    fixer: PRFixer,
    owner: str,
    repo_name: str,
    pr_data: dict,
    fix_title: bool,
    fix_body: bool,
    dry_run: bool,
    quiet: bool,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Process a single PR to fix title and/or body.
    
    Args:
        client: GitHub API client
        fixer: PR fixer instance
        owner: Repository owner
        repo_name: Repository name
        pr_data: PR data from scanner
        fix_title: Whether to fix title
        fix_body: Whether to fix body
        dry_run: Whether this is a dry run
        quiet: Whether to suppress output
        semaphore: Semaphore for concurrency control
        
    Returns:
        True if PR was fixed, False otherwise
    """
    async with semaphore:
        pr_number = pr_data.get("number")
        pr_title = pr_data.get("title", "")
        
        if not quiet:
            console.print(
                f"\n🔄 Processing: {owner}/{repo_name}#{pr_number}"
            )

        try:
            # Get first commit info
            commit_info = await get_first_commit_info(
                client, owner, repo_name, pr_number
            )
            
            if not commit_info:
                if not quiet:
                    console.print(
                        f"[yellow]⚠️  Could not retrieve commit info[/yellow]"
                    )
                return False

            commit_subject = commit_info.get("subject", "").strip()
            commit_body = commit_info.get("body", "").strip()

            changes_needed = False
            changes_made = []

            # Check if title needs fixing
            if fix_title and commit_subject and commit_subject != pr_title:
                changes_needed = True
                if dry_run:
                    if not quiet:
                        console.print(f"   Would update title:")
                        console.print(f"     From: {pr_title}")
                        console.print(f"     To:   {commit_subject}")
                    changes_made.append("title")
                else:
                    # Update PR title
                    success = await update_pr_title(
                        client, owner, repo_name, pr_number, commit_subject
                    )
                    if success:
                        if not quiet:
                            console.print(f"   ✅ Updated title: {commit_subject}")
                        changes_made.append("title")
                    else:
                        if not quiet:
                            console.print(f"   ❌ Failed to update title")

            # Check if body needs fixing
            if fix_body and commit_body:
                # Get current PR body
                current_body = pr_data.get("body", "").strip()
                
                if commit_body != current_body:
                    changes_needed = True
                    if dry_run:
                        if not quiet:
                            console.print(f"   Would update body")
                            console.print(f"     Length: {len(commit_body)} chars")
                        changes_made.append("body")
                    else:
                        # Update PR body
                        success = await update_pr_body(
                            client, owner, repo_name, pr_number, commit_body
                        )
                        if success:
                            if not quiet:
                                console.print(f"   ✅ Updated body")
                            changes_made.append("body")
                        else:
                            if not quiet:
                                console.print(f"   ❌ Failed to update body")

            if not changes_needed:
                if not quiet:
                    console.print(f"   ℹ️  No changes needed")
                return False

            # Create a comment on the PR if changes were made (not in dry-run)
            if not dry_run and len(changes_made) > 0:
                await create_pr_comment(
                    client, owner, repo_name, pr_number, changes_made
                )

            return len(changes_made) > 0

        except Exception as e:
            if not quiet:
                console.print(f"[red]❌ Error: {e}[/red]")
            return False


async def get_first_commit_info(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
) -> dict[str, str] | None:
    """Get the first commit's message from a PR.
    
    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        
    Returns:
        Dict with 'subject' and 'body' keys, or None if error
    """
    try:
        # Get commits for the PR
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/commits"
        response = await client._request("GET", endpoint)
        
        if not response or not isinstance(response, list) or len(response) == 0:
            return None

        # Get first commit
        first_commit = response[0]
        commit_data = first_commit.get("commit", {})
        message = commit_data.get("message", "")

        # Parse commit message into subject and body
        subject, body = parse_commit_message(message)

        return {
            "subject": subject,
            "body": body,
        }

    except Exception as e:
        console.print(f"[red]Error getting commit info: {e}[/red]")
        return None


def parse_commit_message(message: str) -> tuple[str, str]:
    """Parse a commit message into subject and body.
    
    Removes trailers like 'Signed-off-by:', 'Co-authored-by:', etc.
    
    Args:
        message: Full commit message
        
    Returns:
        Tuple of (subject, body) where body has trailers removed
    """
    lines = message.split("\n")
    
    if not lines:
        return "", ""
    
    # First line is the subject
    subject = lines[0].strip()
    
    # Rest is body (skip empty line after subject if present)
    body_lines = lines[1:]
    
    # Skip leading empty lines
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    
    # Remove trailers from the end
    # Common trailer patterns
    trailer_patterns = [
        r"^Signed-off-by:",
        r"^Co-authored-by:",
        r"^Reviewed-by:",
        r"^Tested-by:",
        r"^Acked-by:",
        r"^Cc:",
        r"^Reported-by:",
        r"^Suggested-by:",
        r"^Fixes:",
        r"^See-also:",
        r"^Link:",
        r"^Bug:",
        r"^Change-Id:",
    ]
    
    # Find where trailers start (from the end)
    trailer_start_idx = len(body_lines)
    
    for i in range(len(body_lines) - 1, -1, -1):
        line = body_lines[i].strip()
        
        # Empty line before trailers is ok
        if not line:
            continue
            
        # Check if this line is a trailer
        is_trailer = False
        for pattern in trailer_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                is_trailer = True
                break
        
        if is_trailer:
            # This line and everything after is a trailer
            trailer_start_idx = i
        else:
            # Found a non-trailer, non-empty line, stop looking
            break
    
    # Get body without trailers
    body_lines = body_lines[:trailer_start_idx]
    
    # Remove trailing empty lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    
    body = "\n".join(body_lines).strip()
    
    return subject, body


async def update_pr_title(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    new_title: str,
) -> bool:
    """Update a PR's title.
    
    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        new_title: New title to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        data = {"title": new_title}
        
        response = await client._request("PATCH", endpoint, json=data)
        
        # If successful, trigger re-run of failed checks
        if response is not None:
            await rerun_failed_checks(client, owner, repo, pr_number)
        
        return response is not None

    except Exception as e:
        console.print(f"[red]Error updating PR title: {e}[/red]")
        return False


async def update_pr_body(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    new_body: str,
) -> bool:
    """Update a PR's body.
    
    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        new_body: New body to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        data = {"body": new_body}
        
        response = await client._request("PATCH", endpoint, json=data)
        
        # If successful, trigger re-run of failed checks
        if response is not None:
            await rerun_failed_checks(client, owner, repo, pr_number)
        
        return response is not None

    except Exception as e:
        console.print(f"[red]Error updating PR body: {e}[/red]")
        return False


async def rerun_failed_checks(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
) -> None:
    """Re-run failed checks on a PR after updates.
    
    This function attempts to trigger a re-run of failed checks by:
    1. Getting the head SHA of the PR
    2. Finding failed check runs for that SHA
    3. Re-requesting each failed check run
    
    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
    """
    try:
        # Get PR to find head SHA
        pr_endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_data = await client._request("GET", pr_endpoint)
        
        if not pr_data:
            return
        
        head_sha = pr_data.get("head", {}).get("sha")
        if not head_sha:
            return
        
        # Get check runs for this commit
        checks_endpoint = f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs"
        checks_data = await client._request("GET", checks_endpoint)
        
        if not checks_data:
            return
        
        check_runs = checks_data.get("check_runs", [])
        
        # Find failed or cancelled check runs
        failed_runs = [
            run for run in check_runs
            if run.get("conclusion") in ["failure", "cancelled", "timed_out", "action_required"]
            and run.get("status") == "completed"
        ]
        
        # Re-run each failed check
        for run in failed_runs:
            run_id = run.get("id")
            if run_id:
                try:
                    rerun_endpoint = f"/repos/{owner}/{repo}/check-runs/{run_id}/rerequest"
                    await client._request("POST", rerun_endpoint)
                except Exception:
                    # Silently ignore errors - not all checks support re-run
                    pass
        
    except Exception:
        # Silently ignore errors - re-running checks is best-effort
        pass


async def create_pr_comment(
    client: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    changes_made: list[str],
) -> None:
    """Create a comment on the PR summarizing the fixes applied.
    
    Args:
        client: GitHub API client
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        changes_made: List of changes made (e.g., ["title", "body"])
    """
    try:
        # Build the comment body
        lines = [
            "## 🛠️ Pull Request Fixer",
            "",
            "Automatically fixed pull request metadata:",
        ]
        
        # Add specific fixes
        if "title" in changes_made:
            lines.append("- **Pull request title** updated to match first commit")
        if "body" in changes_made:
            lines.append("- **Pull request body** updated to match commit message")
        
        lines.extend([
            "",
            "---",
            "*This fix was automatically applied by "
            "[pull-request-fixer](https://github.com/lfit/pull-request-fixer)*",
        ])
        
        comment_body = "\n".join(lines)
        
        # Create the comment
        endpoint = f"/repos/{owner}/{repo}/issues/{pr_number}/comments"
        data = {"body": comment_body}
        
        await client._request("POST", endpoint, json=data)
        
    except Exception:
        # Silently ignore errors - commenting is best-effort
        pass


def cli() -> None:
    """CLI entry point."""
    typer.run(main)


if __name__ == "__main__":
    cli()