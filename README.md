# 🔍 LLM PR Review Analyzer

Analyze GitHub PR review comments using Large Language Models to extract insights and patterns from code review feedback.

## 🎯 Features

- **GitHub Integration**: Fetch PR review comments via GitHub API (supports Enterprise GitHub)
- **Intelligent Analysis**: Use LLM to categorize and analyze review patterns
- **5-Section Report Format**: Structured analysis with core insights, action items, mentoring guidance, style insights, and reviewer responses
- **Multiple Output Formats**: CLI display and Markdown file output
- **Enterprise GitHub Support**: Works with custom GitHub instances
- **Rich CLI Interface**: Beautiful command-line interface with progress indicators

## 🏗️ Architecture

```text
┌──────────────────────┐
│ 1. PR Review Fetcher │  ◀── GitHub API (Enterprise supported)
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ 2. Comment Preparer  │  ←─ Data cleaning, grouping by reviewer
└────────┬─────────────┘
         │
         ▼
┌────────────────────────────┐
│ 3. LLM Analysis Pipeline   │  ←─ LangChain + OpenAI
└────────┬───────────────────┘
         │
         ▼
┌──────────────────────┐
│ 4. Output Formatter  │  ←─ 5-section Markdown report
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│   5. CLI Interface   │  ←─ Typer + Rich
└──────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/jason8745/llm-pr-review-analyzer.git
cd llm-pr-review-analyzer

# Install dependencies using uv (recommended)
uv sync
```

### 2. Configuration

Create a configuration file from the example:

```bash
cp src/config/config.example.yaml src/config/config.yaml
```

Edit `src/config/config.yaml` and add your API keys and settings:

```yaml
# LLM PR Review Analyzer Configuration

github:
  token: "your_github_personal_access_token_here"
  api_base_url: "https://api.github.com"  # or Enterprise GitHub URL

llm:
  temperature: 0.1
  max_tokens: 4000
  retry: 3

azure_openai:
  endpoint: "https://your-openai-resource.openai.azure.com/"
  api_version: "2024-02-15-preview"
  deployment: "gpt-4"
  api_key: "your_azure_openai_api_key_here"

app:
  log_level: "INFO"
  max_comments_per_request: 100
```

### 3. Basic Usage

```bash
# Analyze a GitHub.com PR
uv run python main.py analyze "https://github.com/microsoft/vscode/pull/12345"

# Save results to a specific file
uv run python main.py analyze "https://github.com/owner/repo/pull/123" --save-to results.md

# Enable verbose output
uv run python main.py analyze "https://github.com/owner/repo/pull/123" --verbose

# Check configuration
uv run python main.py config-check
```

**Note**: Make sure your `src/config/config.yaml` file is properly configured before running analysis commands.

## 📖 Detailed Usage

### Command Options

```bash
uv run python main.py analyze [PR_URL] [OPTIONS]
```

**Arguments:**

- `PR_URL`: Full GitHub PR URL (supports GitHub.com and Enterprise GitHub)

**Options:**

- `--save-to PATH`: Save output to specific file (auto-generated if not provided)
- `--verbose, -v`: Enable verbose output

### Example Analysis Report Structure

The tool generates a comprehensive 5-section analysis report:

1. **🧠 Core Knowledge Insights**: Key technical knowledge areas demonstrated by reviewers
2. **🎯 Immediate Action Items**: Specific, actionable items extracted from review comments
3. **🎓 Mentoring-level Technical Guidance**: High-level technical guidance and best practices
4. **✨ Valuable Code Style Insights**: Development philosophy and professional habits
5. **💬 Reviewer Response Suggestions**: Professional English responses with Copilot instructions

## 🔧 Development

### Project Structure

```text
src/
├── pr_fetcher.py          # GitHub API integration
├── comment_preparer.py    # Data preprocessing and grouping
├── analyzer_chain.py      # LangChain LLM analysis pipeline
├── output_formatter.py    # Markdown report generation
├── cli.py                 # CLI interface
├── models/               # Data models
│   ├── github_data.py    # GitHub data structures
│   └── analysis_result.py # Analysis result models
├── analysis_helpers/     # Analysis utilities
│   ├── insight_extractor.py
│   ├── profile_builder.py
│   ├── prompt_templates.py
│   └── response_parser.py
├── utils/               # Utility functions
│   ├── exceptions.py
│   ├── logging_config.py
│   └── chain_utils.py
└── config/              # Configuration management
    └── config.py
```

### Running with uv (Recommended)

```bash

# Install dependencies
uv sync

# Run the application
uv run python main.py analyze "PR_URL_HERE"

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Format code
uv run ruff format src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

## 🔑 API Keys Setup

### GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with these scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories)
3. Copy the token to your `src/config/config.yaml` file

### Azure OpenAI API Key

1. Visit [Azure OpenAI Service](https://portal.azure.com/)
2. Create or access your Azure OpenAI resource
3. Get your endpoint URL, deployment name, and API key
4. Copy these values to your `src/config/config.yaml` file

### Enterprise GitHub Configuration

For Enterprise GitHub instances, update the `api_base_url` in your config:

```yaml
github:
  token: "your_token_here"
  api_base_url: "https://your-enterprise.github.com/api/v3"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `uv run pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for LLM orchestration
- [Azure OpenAI Service](https://azure.microsoft.com/en-us/products/ai-services/openai-service) for LLM capabilities
- [Typer](https://github.com/tiangolo/typer) for CLI interface
- [Rich](https://github.com/willmcgugan/rich) for beautiful terminal output
- [uv](https://github.com/astral-sh/uv) for fast Python package management
- [Pydantic](https://github.com/pydantic/pydantic) for configuration management

## 📈 Status & Roadmap

- [x] GitHub API integration (supports Enterprise GitHub)
- [x] LLM analysis pipeline with LangChain + Azure OpenAI
- [x] 5-section structured report generation
- [x] Rich CLI interface with progress indicators
- [x] Markdown output format
- [x] YAML-based configuration system
- [ ] JSON output format
- [ ] Multi-PR comparison features
- [ ] Custom prompt templates
- [ ] Advanced reviewer behavior analysis
- [ ] Web dashboard interface

## 🐛 Issues & Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/jason8745/llm-pr-review-analyzer/issues) page
2. Create a new issue with detailed information
3. Include error messages and steps to reproduce

## 📊 Project Status

![GitHub](https://img.shields.io/github/license/jason8745/llm-pr-review-analyzer)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Status](https://img.shields.io/badge/status-beta-orange.svg)
