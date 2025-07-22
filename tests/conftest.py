"""Test configuration and fixtures."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from config.config import AppConfig, Config, GitHubConfig, LLMConfig
from models import PullRequestInfo, ReviewComment, ReviewData, ReviewState


@pytest.fixture
def mock_github_config():
    """Mock GitHub configuration for testing."""
    return GitHubConfig(
        token=SecretStr("test_github_token"), api_base_url="https://api.github.com"
    )


@pytest.fixture
def mock_llm_config():
    """Mock LLM configuration for testing."""
    return LLMConfig(temperature=0.1, max_tokens=4000, retry=3)


@pytest.fixture
def mock_app_config():
    """Mock app configuration for testing."""
    return AppConfig(log_level="INFO", max_comments_per_request=100)


@pytest.fixture
def mock_config(mock_github_config, mock_llm_config, mock_app_config):
    """Complete mock configuration for testing."""
    return Mock(github=mock_github_config, llm=mock_llm_config, app=mock_app_config)


@pytest.fixture
def patch_get_config(mock_config):
    """Patch get_config function to return mock configuration."""
    with patch("config.config.get_config", return_value=mock_config):
        yield mock_config


@pytest.fixture
def sample_review_comment():
    """Sample review comment for testing."""
    return ReviewComment(
        id=12345,
        author="reviewer1",
        content="This function could be optimized for better performance.",
        timestamp=datetime(2025, 7, 16, 10, 30, 0),
        file_path="src/main.py",
        line_number=42,
        commit_sha="abc123def456",
        review_id=67890,
    )


@pytest.fixture
def sample_pr_info():
    """Sample PR info for testing."""
    return PullRequestInfo(
        number=123,
        title="Add new feature",
        author="developer1",
        created_at=datetime(2025, 7, 15, 9, 0, 0),
        updated_at=datetime(2025, 7, 16, 11, 0, 0),
        state="open",
        base_branch="main",
        head_branch="feature/new-feature",
        repository="owner/repo",
        url="https://github.com/owner/repo/pull/123",
    )


@pytest.fixture
def sample_review_data(sample_pr_info):
    """Sample review data with multiple comments."""
    comments = [
        ReviewComment(
            id=1,
            author="reviewer1",
            content="Please add error handling here.",
            timestamp=datetime(2025, 7, 16, 10, 0, 0),
            file_path="src/main.py",
            line_number=25,
        ),
        ReviewComment(
            id=2,
            author="reviewer2",
            content="Consider using a more descriptive variable name.",
            timestamp=datetime(2025, 7, 16, 10, 15, 0),
            file_path="src/utils.py",
            line_number=10,
        ),
        ReviewComment(
            id=3,
            author="dependabot[bot]",
            content="Bump dependency version",
            timestamp=datetime(2025, 7, 16, 10, 30, 0),
        ),
    ]

    review_states = {
        "reviewer1": ReviewState.CHANGES_REQUESTED,
        "reviewer2": ReviewState.APPROVED,
    }

    return ReviewData(
        pr_info=sample_pr_info,
        comments=comments,
        review_states=review_states,
        total_comments=0,  # Will be calculated
        unique_reviewers=0,  # Will be calculated
    )


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    with patch("src.pr_fetcher.Github") as mock_github:
        # Setup mock repository
        mock_repo = Mock()
        mock_repo.get_pull.return_value = Mock()

        # Setup mock GitHub instance
        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance

        yield mock_github_instance
