"""Tests for PR fetcher module."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import SecretStr

from config.config import GitHubConfig
from models import PullRequestInfo, ReviewComment, ReviewData, ReviewState
from pr_fetcher import GitHubClient
from utils import GitHubAPIError, PullRequestNotFoundError, RepositoryNotFoundError


class TestGitHubClient:
    """Test cases for GitHubClient class."""

    def test_init_with_token(self):
        """Test GitHubClient initialization with explicit token."""
        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient(token="explicit_token")

            assert client.token == "explicit_token"
            mock_github.assert_called_once()

    def test_init_with_base_url(self):
        """Test GitHubClient initialization with base URL."""
        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient(
                token="test_token", base_url="https://enterprise.github.com/api/v3"
            )

            assert client.token == "test_token"
            mock_github.assert_called_once_with(
                auth=mock_github.call_args[1]["auth"],
                base_url="https://enterprise.github.com/api/v3",
            )

    def test_init_with_custom_config(self):
        """Test GitHubClient initialization with custom configuration."""
        # Create test config
        test_config = GitHubConfig(
            token=SecretStr("test_token"), api_base_url="https://test.github.com/api/v3"
        )

        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient(config=test_config)

            assert client.token == "test_token"
            mock_github.assert_called_once_with(
                auth=mock_github.call_args[1]["auth"],
                base_url="https://test.github.com/api/v3",
            )

    def test_init_with_explicit_params_override_config(self):
        """Test that explicit parameters override config values."""
        test_config = GitHubConfig(
            token=SecretStr("config_token"),
            api_base_url="https://config.github.com/api/v3",
        )

        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient(
                token="explicit_token",
                base_url="https://explicit.github.com/api/v3",
                config=test_config,
            )

            assert client.token == "explicit_token"
            mock_github.assert_called_once_with(
                auth=mock_github.call_args[1]["auth"],
                base_url="https://explicit.github.com/api/v3",
            )

    @patch("config.config.get_config")
    def test_init_without_config_uses_global(self, mock_get_config):
        """Test fallback to global config when no config provided."""
        # Setup mock config
        mock_config = Mock()
        mock_config.github.token.get_secret_value.return_value = "global_token"
        mock_config.github.api_base_url = "https://api.github.com"
        mock_get_config.return_value = mock_config

        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient()

            assert client.token == "global_token"
            mock_get_config.assert_called_once()
            mock_github.assert_called_once()

    @patch("config.config.get_config")
    def test_init_enterprise_github_from_config(self, mock_get_config):
        """Test enterprise GitHub setup from config."""
        # Setup mock config
        mock_config = Mock()
        mock_config.github.token.get_secret_value.return_value = "enterprise_token"
        mock_config.github.api_base_url = "https://enterprise.github.com/api/v3"
        mock_get_config.return_value = mock_config

        with patch("pr_fetcher.Github") as mock_github:
            client = GitHubClient()

            assert client.token == "enterprise_token"
            mock_github.assert_called_once_with(
                auth=mock_github.call_args[1]["auth"],
                base_url="https://enterprise.github.com/api/v3",
            )

    def test_check_rate_limit_normal(self):
        """Test rate limit checking with normal limits."""
        with patch("pr_fetcher.Github") as mock_github:
            # Setup mock rate limit
            mock_rate_limit = Mock()
            mock_rate_limit.core.remaining = 1000
            mock_rate_limit.core.reset.timestamp.return_value = 1234567890

            mock_github_instance = Mock()
            mock_github_instance.get_rate_limit.return_value = mock_rate_limit
            mock_github.return_value = mock_github_instance

            client = GitHubClient(token="test_token")
            client._check_rate_limit()

            assert client._rate_limit_remaining == 1000
            assert client._rate_limit_reset == 1234567890

    def test_check_rate_limit_low_remaining(self):
        """Test rate limit checking with low remaining requests."""
        from utils import RateLimitError

        with patch("pr_fetcher.Github") as mock_github:
            # Setup mock rate limit with low remaining
            mock_rate_limit = Mock()
            mock_rate_limit.core.remaining = 5  # Below safety buffer
            mock_rate_limit.core.reset.timestamp.return_value = 1234567890

            mock_github_instance = Mock()
            mock_github_instance.get_rate_limit.return_value = mock_rate_limit
            mock_github.return_value = mock_github_instance

            client = GitHubClient(token="test_token")

            with pytest.raises(RateLimitError):
                client._check_rate_limit()

    def test_get_repository_success(self):
        """Test successful repository retrieval."""
        with patch("pr_fetcher.Github") as mock_github:
            mock_repo = Mock()
            mock_github_instance = Mock()
            mock_github_instance.get_repo.return_value = mock_repo
            mock_github_instance.get_rate_limit.return_value = Mock(
                core=Mock(
                    remaining=1000, reset=Mock(timestamp=Mock(return_value=1234567890))
                )
            )
            mock_github.return_value = mock_github_instance

            client = GitHubClient(token="test_token")
            result = client.get_repository("owner/repo")

            assert result == mock_repo
            mock_github_instance.get_repo.assert_called_once_with("owner/repo")

    def test_get_repository_not_found(self):
        """Test repository not found error."""
        from github import GithubException

        with patch("pr_fetcher.Github") as mock_github:
            mock_github_instance = Mock()
            mock_github_instance.get_rate_limit.return_value = Mock(
                core=Mock(
                    remaining=1000, reset=Mock(timestamp=Mock(return_value=1234567890))
                )
            )
            mock_github_instance.get_repo.side_effect = GithubException(
                404, "Not Found"
            )
            mock_github.return_value = mock_github_instance

            client = GitHubClient(token="test_token")

            with pytest.raises(RepositoryNotFoundError):
                client.get_repository("owner/nonexistent")

    def test_convert_review_comment(self):
        """Test conversion of GitHub review comment."""
        with patch("pr_fetcher.Github"):
            client = GitHubClient(token="test_token")

            # Mock GitHub comment object
            mock_comment = Mock()
            mock_comment.id = 12345
            mock_comment.user.login = "reviewer1"
            mock_comment.body = "This needs improvement"
            mock_comment.created_at = "2025-07-21T10:00:00Z"
            mock_comment.path = "src/main.py"
            mock_comment.position = 42
            mock_comment.commit_id = "abc123"
            mock_comment.pull_request_review_id = 67890

            result = client._convert_review_comment(mock_comment)

            assert isinstance(result, ReviewComment)
            assert result.id == 12345
            assert result.author == "reviewer1"
            assert result.content == "This needs improvement"
            assert result.file_path == "src/main.py"
            assert result.line_number == 42
            assert result.commit_sha == "abc123"
            assert result.review_id == 67890

    def test_convert_issue_comment(self):
        """Test conversion of GitHub issue comment."""
        with patch("pr_fetcher.Github"):
            client = GitHubClient(token="test_token")

            # Mock GitHub issue comment object
            mock_comment = Mock()
            mock_comment.id = 54321
            mock_comment.user.login = "commenter1"
            mock_comment.body = "Great work!"
            mock_comment.created_at = "2025-07-21T11:00:00Z"

            result = client._convert_issue_comment(mock_comment)

            assert isinstance(result, ReviewComment)
            assert result.id == 54321
            assert result.author == "commenter1"
            assert result.content == "Great work!"
            assert result.file_path is None
            assert result.line_number is None

    def test_extract_pr_info(self):
        """Test PR info extraction."""
        with patch("pr_fetcher.Github"):
            client = GitHubClient(token="test_token")

            # Mock PR object
            mock_pr = Mock()
            mock_pr.number = 123
            mock_pr.title = "Test PR"
            mock_pr.user.login = "author1"
            mock_pr.created_at = "2025-07-21T09:00:00Z"
            mock_pr.updated_at = "2025-07-21T12:00:00Z"
            mock_pr.state = "open"
            mock_pr.base.ref = "main"
            mock_pr.head.ref = "feature-branch"
            mock_pr.html_url = "https://github.com/owner/repo/pull/123"

            result = client._extract_pr_info(mock_pr, "owner/repo")

            assert isinstance(result, PullRequestInfo)
            assert result.number == 123
            assert result.title == "Test PR"
            assert result.author == "author1"
            assert result.state == "open"
            assert result.base_branch == "main"
            assert result.head_branch == "feature-branch"
            assert result.repository == "owner/repo"
            assert result.url == "https://github.com/owner/repo/pull/123"


class TestGitHubClientIntegration:
    """Integration tests for GitHubClient (require network access)."""

    @pytest.mark.skip(reason="Integration test - requires valid GitHub token")
    def test_fetch_real_pr_reviews(self):
        """Test fetching real PR reviews (integration test)."""
        # This test should be run manually with a valid token
        # and a known public repository
        client = GitHubClient(token="your_real_token_here")

        try:
            result = client.fetch_pr_reviews("octocat/Hello-World", 1)
            assert isinstance(result, ReviewData)
            assert result.pr_info.number == 1
        except Exception as e:
            pytest.skip(f"Integration test failed: {e}")
