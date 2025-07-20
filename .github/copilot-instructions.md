---
description: 'LLM PR Review Analyzer - Python coding conventions and project-specific guidelines'
applyTo: '**/*.py'
---

# LLM PR Review Analyzer - Coding Guidelines

## Project Architecture Overview

This project analyzes GitHub PR review comments using LLM to extract insights and patterns. The architecture consists of:

1. **PR Review Fetcher** - GitHub API integration for fetching review data (supports Enterprise GitHub)
2. **Comment Preparer** - Data cleaning, grouping, and preprocessing by reviewer
3. **LLM Analysis Pipeline** - LangChain-based analysis using Azure OpenAI
4. **Output Formatter** - 5-section Markdown report generation
5. **CLI Interface** - User-friendly command-line interface using Typer

## Python Coding Standards

### Type Annotations & Documentation
- Use comprehensive type hints for all functions, including `Optional`, `Union`, `List`, `Dict`
- Provide detailed docstrings following Google style for complex functions
- Include parameter types, return types, and example usage for public APIs
- Document exceptions that functions may raise

```python
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

@dataclass
class ReviewComment:
    """Represents a single GitHub review comment."""
    author: str
    content: str
    timestamp: str
    file_path: Optional[str] = None
    
def fetch_pr_reviews(
    repo: str, 
    pr_number: int, 
    github_token: str
) -> List[ReviewComment]:
    """
    Fetch all review comments for a specific PR.
    
    Args:
        repo: Repository name in format 'owner/repo'
        pr_number: Pull request number
        github_token: GitHub personal access token
        
    Returns:
        List of ReviewComment objects containing review data
        
    Raises:
        GitHubAPIError: When API request fails
        ValidationError: When repo format is invalid
        
    Example:
        >>> comments = fetch_pr_reviews("user/repo", 123, "token")
        >>> len(comments)
        5
    """
```

### Project-Specific Patterns

#### 1. Configuration Management
- Use Pydantic for configuration validation and YAML files for configuration storage
- Store API keys and settings in `src/config/config.yaml`
- Provide clear configuration examples with `config.example.yaml`

```python
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings
import yaml

class GitHubConfig(BaseModel):
    """GitHub API configuration."""
    token: SecretStr
    api_base_url: str = "https://api.github.com"

class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration."""
    endpoint: str
    api_version: str = "2024-02-15-preview"
    deployment: str
    api_key: SecretStr

class Config(BaseSettings):
    """Application configuration with validation."""
    github: GitHubConfig
    azure_openai: AzureOpenAIConfig
    app: AppConfig
```

#### 2. Error Handling Strategy
- Create custom exception classes for different error types
- Use structured logging for debugging GitHub API issues
- Implement retry logic for API calls with exponential backoff

```python
class GitHubAPIError(Exception):
    """Raised when GitHub API requests fail."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"GitHub API error {status_code}: {message}")

class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""
    pass

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass
```

#### 3. Data Processing Patterns
- Use dataclasses or Pydantic models for structured data
- Implement data validation at module boundaries
- Create small, composable functions for data transformations

```python
def group_comments_by_reviewer(
    comments: List[ReviewComment]
) -> Dict[str, List[ReviewComment]]:
    """Group review comments by reviewer author."""
    from collections import defaultdict
    grouped = defaultdict(list)
    for comment in comments:
        if not comment.author.endswith('[bot]'):  # Exclude bots
            grouped[comment.author].append(comment)
    return dict(grouped)
```

#### 4. LangChain Integration
- Use structured prompts with clear input/output schemas
- Implement prompt templates for consistency
- Add fallback mechanisms for LLM failures

```python
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

class ReviewAnalysisParser(BaseOutputParser):
    """Parse LLM output into structured review insights."""
    
    def parse(self, text: str) -> Dict[str, any]:
        """Parse LLM response into structured data."""
        # Implementation here
        pass
```

## Code Organization & Modularity

### Module Structure
```
src/
├── pr_fetcher.py          # GitHub API integration
├── comment_preparer.py    # Data preprocessing and grouping
├── analyzer_chain.py      # LangChain LLM analysis pipeline
├── output_formatter.py    # Markdown report generation
├── cli.py                 # CLI interface
├── models/               # Data models
│   ├── __init__.py
│   ├── github_data.py
│   └── analysis_result.py
├── analysis_helpers/     # Analysis utilities
│   ├── __init__.py
│   ├── insight_extractor.py
│   ├── profile_builder.py
│   ├── prompt_templates.py
│   └── response_parser.py
├── utils/               # Utility functions
│   ├── __init__.py
│   ├── exceptions.py
│   ├── logging_config.py
│   └── chain_utils.py
└── config/              # Configuration management
    ├── __init__.py
    ├── config.py
    ├── config.yaml
    └── config.example.yaml
```

### Function Design Principles
- Each function should have a single responsibility
- Keep functions under 50 lines when possible
- Use descriptive parameter names
- Return structured data types, not primitive types for complex operations

## Testing Strategy

### Test Coverage Requirements
- Unit tests for all data processing functions
- Integration tests for GitHub API interactions
- Mock LLM responses for testing analysis pipeline
- CLI testing using Typer's testing utilities

```python
import pytest
from unittest.mock import Mock, patch
from your_module import fetch_pr_reviews

def test_fetch_pr_reviews_success():
    """Test successful PR review fetching."""
    with patch('your_module.github_client') as mock_client:
        mock_client.get_pr_reviews.return_value = [
            {"user": {"login": "reviewer1"}, "body": "LGTM"}
        ]
        result = fetch_pr_reviews("owner/repo", 123, "token")
        assert len(result) == 1
        assert result[0].author == "reviewer1"

def test_fetch_pr_reviews_api_error():
    """Test handling of GitHub API errors."""
    with patch('your_module.github_client') as mock_client:
        mock_client.get_pr_reviews.side_effect = GitHubAPIError(404, "Not found")
        with pytest.raises(GitHubAPIError):
            fetch_pr_reviews("owner/repo", 999, "token")
```

### Running Tests with uv
```bash
# Install test dependencies
uv add --dev pytest pytest-cov pytest-mock

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_pr_fetcher.py -v
```

## Dependency Management

### Using uv for Package Management
- Use `uv` as the primary dependency management tool
- Add dependencies with `uv add package_name`
- Add development dependencies with `uv add --dev package_name`
- Use `uv sync` to install all dependencies from lock file
- Use `uv run` to execute scripts in the virtual environment

```bash
# Add runtime dependencies
uv add pydantic
uv add langchain
uv add typer[all]

# Add development dependencies
uv add --dev pytest
uv add --dev pytest-cov
uv add --dev ruff

# Install all dependencies
uv sync

# Run scripts
uv run python main.py
uv run pytest
```

### Virtual Environment Management
- `uv` automatically manages virtual environments
- Use `uv run` instead of activating environments manually
- Dependencies are automatically resolved and locked in `uv.lock`

## Performance & Security Guidelines

### API Usage Optimization
- Implement caching for GitHub API responses
- Use pagination for large datasets
- Respect GitHub API rate limits with proper delays

### Security Best Practices
- Never log or print API tokens
- Validate all external inputs
- Use environment variables for sensitive configuration
- Implement input sanitization for user-provided repository names

### Memory Management
- Process large comment datasets in chunks
- Use generators for memory-efficient data processing
- Clear large objects when no longer needed

### Code Quality Tools with uv
```bash
# Add code quality tools
uv add --dev ruff black mypy pre-commit

# Format code
uv run ruff format src/ tests/

# Lint code  
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Run all quality checks
uv run pre-commit run --all-files
```

## CLI Design Patterns

Use Typer for consistent CLI interface:

```python
import typer
from typing import Optional

app = typer.Typer(help="LLM PR Review Analyzer")

@app.command()
def analyze(
    pr_url: str = typer.Argument(..., help="GitHub PR URL"),
    save_to: Optional[str] = typer.Option(None, help="Save output to file"),
    verbose: bool = typer.Option(False, help="Enable verbose output")
):
    """Analyze PR review comments and generate insights."""
    try:
        # Implementation here
        typer.echo("Analysis completed successfully!")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
```

## Documentation Requirements

- Include usage examples in README.md
- Document all CLI commands and options
- Provide sample configuration files
- Add troubleshooting guide for common API issues
- Include examples of LLM prompt engineering

## Current Implementation Notes

### Report Structure
The system generates a standardized 5-section analysis report:
1. **Core Knowledge Insights** - Technical expertise demonstrated by reviewers
2. **Immediate Action Items** - Specific actionable feedback
3. **Mentoring-level Technical Guidance** - High-level guidance and best practices
4. **Valuable Code Style Insights** - Development philosophy and professional habits
5. **Reviewer Response Suggestions** - Professional responses with Copilot instructions

### Configuration System
- YAML-based configuration in `src/config/config.yaml`
- Pydantic models for validation and type safety
- Support for both GitHub.com and Enterprise GitHub instances
- Azure OpenAI integration (not standard OpenAI)

### Key Dependencies
- **LangChain**: For LLM orchestration and prompt management
- **Azure OpenAI**: Primary LLM provider
- **Typer + Rich**: CLI interface with beautiful output
- **Pydantic**: Configuration management and data validation
- **uv**: Package management and virtual environment

Remember: This project handles external APIs and user data, so prioritize error handling, logging, and user experience in all implementations.