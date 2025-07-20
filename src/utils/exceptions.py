"""Custom exception classes for the application."""


class LLMPRAnalyzerError(Exception):
    """Base exception class for LLM PR Review Analyzer."""

    pass


class GitHubAPIError(LLMPRAnalyzerError):
    """Raised when GitHub API requests fail."""

    def __init__(self, status_code: int, message: str, response_data: dict = None):
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(f"GitHub API error {status_code}: {message}")


class RateLimitError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_time: int = None):
        self.reset_time = reset_time
        message = "GitHub API rate limit exceeded"
        if reset_time:
            message += f". Resets at {reset_time}"
        super().__init__(429, message)


class RepositoryNotFoundError(GitHubAPIError):
    """Raised when repository is not found or not accessible."""

    def __init__(self, repo: str):
        self.repo = repo
        super().__init__(404, f"Repository '{repo}' not found or not accessible")


class PullRequestNotFoundError(GitHubAPIError):
    """Raised when pull request is not found."""

    def __init__(self, repo: str, pr_number: int):
        self.repo = repo
        self.pr_number = pr_number
        super().__init__(404, f"Pull request #{pr_number} not found in '{repo}'")


class LLMAnalysisError(LLMPRAnalyzerError):
    """Raised when LLM analysis fails."""

    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(f"LLM analysis failed: {message}")


class ConfigurationError(LLMPRAnalyzerError):
    """Raised when configuration is invalid."""

    pass


class DataValidationError(LLMPRAnalyzerError):
    """Raised when data validation fails."""

    pass
