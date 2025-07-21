"""GitHub API client for fetching PR review data."""

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from github import Auth, Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

if TYPE_CHECKING:
    from config.config import GitHubConfig

from models import PullRequestInfo, ReviewComment, ReviewData, ReviewState
from utils import (
    GitHubAPIError,
    PullRequestNotFoundError,
    RateLimitError,
    RepositoryNotFoundError,
    get_logger,
)

logger = get_logger(__name__)


class GitHubClient:
    """GitHub API client for fetching PR review data."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional["GitHubConfig"] = None,
    ):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token. If provided, overrides config.
            base_url: GitHub API base URL for enterprise instances.
            config: GitHubConfig object. If None, uses global config.
        """
        # Use dependency injection pattern
        if config is None:
            from config.config import get_config

            config = get_config().github

        # Priority: explicit token > config token
        self.token = token or config.token.get_secret_value()

        # Use base_url from parameter or config
        api_base_url = base_url or config.api_base_url

        # Create authentication object
        auth = Auth.Token(self.token)

        # Configure for enterprise GitHub if base_url provided
        if api_base_url != "https://api.github.com":
            self.github = Github(auth=auth, base_url=api_base_url)
        else:
            self.github = Github(auth=auth)

        self._rate_limit_remaining = None
        self._rate_limit_reset = None

    def _check_rate_limit(self) -> None:
        """Check and handle GitHub API rate limiting."""
        try:
            rate_limit = self.github.get_rate_limit()
            core_limit = rate_limit.core

            self._rate_limit_remaining = core_limit.remaining
            self._rate_limit_reset = core_limit.reset.timestamp()

            if core_limit.remaining < 10:  # Safety buffer
                reset_time = int(core_limit.reset.timestamp())
                logger.warning(
                    f"GitHub API rate limit low: {core_limit.remaining} remaining"
                )
                raise RateLimitError(reset_time)

        except GithubException as e:
            # Some GitHub instances (like enterprise) may not support rate limiting API
            if e.status == 404 and "Rate limiting is not enabled" in str(e):
                logger.info("Rate limiting API not available on this GitHub instance")
                self._rate_limit_remaining = 5000  # Assume plenty of requests available
                self._rate_limit_reset = time.time() + 3600  # Reset in 1 hour
                return
            elif e.status == 403:
                raise RateLimitError()
            raise GitHubAPIError(e.status, str(e))

    def get_repository(self, repo_name: str) -> Repository:
        """
        Get repository object.

        Args:
            repo_name: Repository name in format 'owner/repo'

        Returns:
            GitHub Repository object

        Raises:
            RepositoryNotFoundError: If repository not found or not accessible
            GitHubAPIError: For other API errors
        """
        try:
            self._check_rate_limit()
            return self.github.get_repo(repo_name)
        except GithubException as e:
            if e.status == 404:
                raise RepositoryNotFoundError(repo_name)
            elif e.status == 403:
                raise RateLimitError()
            else:
                raise GitHubAPIError(e.status, str(e))

    def fetch_pr_reviews(self, repo_name: str, pr_number: int) -> ReviewData:
        """
        Fetch all review comments for a specific PR.

        Args:
            repo_name: Repository name in format 'owner/repo'
            pr_number: Pull request number

        Returns:
            ReviewData object containing all review information

        Raises:
            RepositoryNotFoundError: If repository not found
            PullRequestNotFoundError: If PR not found
            GitHubAPIError: For other API errors
        """
        logger.info(f"Fetching reviews for {repo_name}#{pr_number}")

        try:
            # Get repository and PR
            repo = self.get_repository(repo_name)
            pr = repo.get_pull(pr_number)

            # Get PR basic info
            pr_info = self._extract_pr_info(pr, repo_name)

            # Fetch all comments
            comments = self._fetch_all_comments(pr)

            # Get review states
            review_states = self._get_review_states(pr)

            return ReviewData(
                pr_info=pr_info,
                comments=comments,
                review_states=review_states,
                total_comments=0,  # Will be calculated in __post_init__
                unique_reviewers=0,  # Will be calculated in __post_init__
            )

        except GithubException as e:
            if e.status == 404:
                raise PullRequestNotFoundError(repo_name, pr_number)
            elif e.status == 403:
                raise RateLimitError()
            else:
                raise GitHubAPIError(e.status, str(e))

    def _extract_pr_info(self, pr: PullRequest, repo_name: str) -> PullRequestInfo:
        """Extract PR basic information."""
        return PullRequestInfo(
            number=pr.number,
            title=pr.title,
            author=pr.user.login if pr.user else "unknown",
            created_at=pr.created_at,
            updated_at=pr.updated_at,
            state=pr.state,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            repository=repo_name,
            url=pr.html_url,
        )

    def _fetch_all_comments(self, pr: PullRequest) -> List[ReviewComment]:
        """Fetch all types of comments for a PR."""
        comments = []

        # Review comments (inline comments on code)
        for comment in pr.get_review_comments():
            comments.append(self._convert_review_comment(comment))

        # General PR comments
        for comment in pr.get_issue_comments():
            comments.append(self._convert_issue_comment(comment))

        # Review summaries
        for review in pr.get_reviews():
            if review.body and review.body.strip():
                comments.append(self._convert_review_summary(review))

        logger.info(f"Fetched {len(comments)} total comments")
        return comments

    def _convert_review_comment(self, comment) -> ReviewComment:
        """Convert GitHub review comment to our format."""
        return ReviewComment(
            id=comment.id,
            author=comment.user.login if comment.user else "unknown",
            content=comment.body or "",
            timestamp=comment.created_at,
            file_path=comment.path,
            line_number=comment.position,
            commit_sha=comment.commit_id,
            review_id=comment.pull_request_review_id,
        )

    def _convert_issue_comment(self, comment) -> ReviewComment:
        """Convert GitHub issue comment to our format."""
        return ReviewComment(
            id=comment.id,
            author=comment.user.login if comment.user else "unknown",
            content=comment.body or "",
            timestamp=comment.created_at,
        )

    def _convert_review_summary(self, review) -> ReviewComment:
        """Convert GitHub review summary to our format."""
        return ReviewComment(
            id=review.id,
            author=review.user.login if review.user else "unknown",
            content=review.body or "",
            timestamp=review.submitted_at or review.created_at,
            review_id=review.id,
        )

    def _get_review_states(self, pr: PullRequest) -> Dict[str, ReviewState]:
        """Get the latest review state for each reviewer."""
        review_states = {}

        for review in pr.get_reviews():
            if review.user:
                reviewer = review.user.login
                # Map GitHub states to our enum
                if review.state == "APPROVED":
                    review_states[reviewer] = ReviewState.APPROVED
                elif review.state == "CHANGES_REQUESTED":
                    review_states[reviewer] = ReviewState.CHANGES_REQUESTED
                elif review.state == "COMMENTED":
                    review_states[reviewer] = ReviewState.COMMENTED
                else:
                    review_states[reviewer] = ReviewState.PENDING

        return review_states
