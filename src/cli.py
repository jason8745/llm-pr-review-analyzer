"""Command-line interface for LLM PR Review Analyzer."""

import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from analyzer_chain import ReviewAnalyzer
from comment_preparer import CommentPreparer
from config.config import get_config
from output_formatter import FormatManager
from pr_fetcher import GitHubClient
from utils import ConfigurationError, get_logger, setup_logging

# Initialize console and app
console = Console()
app = typer.Typer(
    name="llm-pr-analyzer",
    help="🔍 Analyze GitHub PR review comments using LLM to extract insights and patterns",
    rich_markup_mode="rich",
)

# Setup logging (delayed until config is loaded)
logger = None


def parse_pr_url(pr_url: str) -> tuple[str, int, Optional[str]]:
    """
    Parse GitHub PR URL to extract repository, PR number, and base URL.

    Args:
        pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123 or enterprise GitHub)

    Returns:
        Tuple of (repo, pr_number, base_url)

    Raises:
        ValueError: If URL format is invalid
    """
    # Support various GitHub PR URL formats including enterprise GitHub
    patterns = [
        # Enterprise GitHub (like adc.github.trendmicro.com)
        r"([^/]+\.github\.[^/]+)/([^/]+/[^/]+)/pull/(\d+)",
        # Regular GitHub
        r"github\.com/([^/]+/[^/]+)/pull/(\d+)",
        r"github\.com/([^/]+/[^/]+)/pulls/(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, pr_url)
        if match:
            if len(match.groups()) == 3:  # Enterprise GitHub
                base_domain = match.group(1)
                repo = match.group(2)
                pr_number = int(match.group(3))
                base_url = f"https://{base_domain}/api/v3"
                return repo, pr_number, base_url
            else:  # Regular GitHub
                repo = match.group(1)
                pr_number = int(match.group(2))
                return repo, pr_number, None

    raise ValueError(f"Invalid GitHub PR URL format: {pr_url}")


@app.command()
def analyze(
    pr_url: str = typer.Argument(
        ..., help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)"
    ),
    save_to: Optional[Path] = typer.Option(
        None, help="Save output to file (optional - auto-generated if not provided)"
    ),
    verbose: bool = typer.Option(False, help="Enable verbose output"),
):
    """🔍 Analyze PR review comments and generate insights."""
    # Setup logging
    try:
        config = get_config()
        if verbose:
            setup_logging("DEBUG")
        else:
            setup_logging(config.app.log_level)
    except ConfigurationError as e:
        console.print(f"⚙️  [bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(1)

    logger = get_logger(__name__)

    try:
        # Parse PR URL
        repo, pr_number, base_url = parse_pr_url(pr_url)
        if base_url:
            console.print(
                f"🔗 Analyzing [bold blue]{repo}[/bold blue] PR [bold green]#{pr_number}[/bold green] on [dim]{base_url}[/dim]"
            )
        else:
            console.print(
                f"🔗 Analyzing [bold blue]{repo}[/bold blue] PR [bold green]#{pr_number}[/bold green]"
            )
        logger.info(
            f"Starting analysis for {repo} PR #{pr_number} (base_url: {base_url})"
        )

        # Show analysis started panel
        with console.status("[bold blue]Fetching PR data..."):
            # Fetch PR review data
            client = GitHubClient(base_url=base_url)
            pr_data = client.fetch_pr_reviews(repo, pr_number)

            if not pr_data:
                console.print("[bold red]No review data found for this PR.[/bold red]")
                raise typer.Exit(1)

        console.print(
            f"📊 Found [bold green]{len(pr_data.comments)}[/bold green] review comments"
        )

        with console.status("[bold blue]Preparing comments for analysis..."):
            # Prepare comments for analysis
            preparer = CommentPreparer()
            prepared_data = preparer.prepare_comments(pr_data)

        console.print(
            f"👥 Grouped into [bold green]{len(prepared_data['grouped_data']['by_reviewer'])}[/bold green] reviewers"
        )

        with console.status("[bold blue]Running LLM analysis..."):
            # Run LLM analysis
            analyzer = ReviewAnalyzer()
            review_data = analyzer.analyze_comments(prepared_data)

        console.print("🧠 [bold green]LLM analysis completed![/bold green]")

        # Output results
        with console.status("[bold blue]Generating Markdown report..."):
            formatter = FormatManager()
            if save_to:
                output_path = save_to
                content = formatter.format_result(review_data)
                formatter.formatter.save_to_file(content, str(save_to))
            else:
                output_path = formatter.save_result(review_data)

        console.print(
            f"✅ [bold green]Analysis completed![/bold green] Report saved to: [bold blue]{output_path}[/bold blue]"
        )

    except ValueError as e:
        console.print(f"🔗 [bold red]URL Error:[/bold red] {e}")
        console.print(
            "[dim]Expected format: https://github.com/owner/repo/pull/123[/dim]"
        )
        raise typer.Exit(1)
    except ConfigurationError as e:
        console.print(f"⚙️  [bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def config_check():
    """🔧 Check configuration and API connectivity."""
    console.print("[bold blue]Checking configuration...[/bold blue]")

    try:
        config = get_config()
    except ConfigurationError as e:
        console.print(f"⚙️  [bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(1)

    # Check environment variables
    config_table = Table(title="Configuration Status")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Status", style="green")
    config_table.add_column("Value", style="dim")

    # GitHub token
    if (
        config.github.token
        and config.github.token.get_secret_value()
        != "your_github_personal_access_token_here"
    ):
        config_table.add_row(
            "GitHub Token",
            "✅ Set",
            f"{'*' * 8}...{config.github.token.get_secret_value()[-4:]}",
        )
    else:
        config_table.add_row("GitHub Token", "❌ Not Set", "Missing")

    # Azure OpenAI API key
    if (
        config.azure_openai.api_key
        and config.azure_openai.api_key.get_secret_value()
        != "your_azure_openai_api_key_here"
    ):
        config_table.add_row(
            "Azure OpenAI API Key",
            "✅ Set",
            f"{'*' * 8}...{config.azure_openai.api_key.get_secret_value()[-4:]}",
        )
    else:
        config_table.add_row("Azure OpenAI API Key", "❌ Not Set", "Missing")

    # Other settings
    config_table.add_row("Log Level", "✅ Set", config.app.log_level)
    config_table.add_row(
        "Max Comments", "✅ Set", str(config.app.max_comments_per_request)
    )
    config_table.add_row("Azure Endpoint", "✅ Set", config.azure_openai.endpoint)
    config_table.add_row("Model", "✅ Set", config.azure_openai.deployment)

    console.print(config_table)

    # Test GitHub API connectivity
    if config.github.token:
        try:
            console.print("\n[bold blue]Testing GitHub API connectivity...[/bold blue]")
            client = GitHubClient()
            rate_limit = client.github.get_rate_limit()
            console.print(
                f"✅ GitHub API: {rate_limit.core.remaining}/{rate_limit.core.limit} requests remaining"
            )
        except Exception as e:
            console.print(f"❌ GitHub API Error: {e}")


@app.command()
def version():
    """📋 Show version information."""
    console.print("[bold blue]LLM PR Review Analyzer[/bold blue]")
    console.print("Version: 0.1.0")
    console.print("Author: Your name")
    console.print("GitHub: https://github.com/your-username/llm-pr-review-analyzer")


if __name__ == "__main__":
    app()
