"""Output formatting module for LLM analysis results."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from models.analysis_result import AnalysisResult, ReviewerProfile, ReviewInsight
from utils import get_logger

logger = get_logger(__name__)


class OutputFormatter:
    """Format analysis results into Markdown format."""

    def __init__(self):
        """Initialize output formatter."""
        pass

    def format_markdown_output(self, result: AnalysisResult) -> str:
        """Format analysis result as Markdown with streamlined 5-section focus."""
        lines = []

        # Header
        lines.extend(
            [
                f"# PR 審查分析報告",
                f"",
                f"**專案：** {result.repository}  ",
                f"**PR：** #{result.pr_number}  ",
                f"**分析日期：** {self._format_timestamp(result.analysis_timestamp)}  ",
                f"**洞察數量：** {len(result.insights)} | **審查者：** {len(result.reviewer_profiles)}",
                f"",
                "---",
                "",
            ]
        )

        # Section 1: Core Knowledge Insights
        if hasattr(result, "key_knowledge_insights") and result.key_knowledge_insights:
            lines.extend(["## 🧠 核心知識洞察", ""])
            for i, insight in enumerate(result.key_knowledge_insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        # Section 2: Immediate Action Items
        if hasattr(result, "learning_opportunities") and result.learning_opportunities:
            immediate_actions = result.learning_opportunities.get(
                "immediate_actions", []
            )
            if immediate_actions:
                lines.extend(["## 🎯 立即行動項目", ""])
                for action in immediate_actions:
                    lines.append(f"- {action}")
                lines.append("")

        # Section 3: Mentoring-level Technical Guidance
        if hasattr(result, "mentoring_insights") and result.mentoring_insights:
            lines.extend(["## 🎓 導師級技術指導", ""])
            for i, insight in enumerate(result.mentoring_insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        # Section 4: Valuable Code Style Insights
        if hasattr(result, "valuable_insights") and result.valuable_insights:
            lines.extend(["## ✨ 值得內化的 Code Style 洞察", ""])
            for category, insights in result.valuable_insights.items():
                if insights:
                    category_name = {
                        "style_forming_comments": "🎨 風格塑造建議",
                        "development_philosophy": "💭 開發理念",
                        "professional_habits": "⚙️ 專業習慣",
                    }.get(category, category.replace("_", " ").title())

                    lines.extend([f"### {category_name}", ""])
                    for insight in insights:
                        lines.append(f"- {insight}")
                    lines.append("")

        # Section 5: Reviewer Response Suggestions (Grouped by Commit Logic)
        commit_groups = result.get_reviewer_responses_by_commit_group()
        commit_messages = result.get_suggested_commit_messages()

        if commit_groups:
            lines.extend(["## 💬 Reviewer 回覆建議 (按 Commit 邏輯分組)", ""])

            for group_name, responses in commit_groups.items():
                if not responses:
                    continue

                # Filter out responses without meaningful Copilot instructions
                meaningful_responses = [
                    r
                    for r in responses
                    if r.copilot_instruction
                    and r.copilot_instruction.strip()
                    and len(r.copilot_instruction.strip()) > 10
                ]

                if not meaningful_responses:
                    continue  # Skip groups with no actionable responses

                # Format group header with suggested commit message
                group_display_name = (
                    group_name.replace("_", " ").replace("-", " ").title()
                )
                lines.extend([f"### 🔄 {group_display_name}", ""])

                if group_name in commit_messages:
                    lines.extend(
                        [
                            f"**建議 Commit Message:** `{commit_messages[group_name]}`",
                            "",
                        ]
                    )

                # Group responses by reviewer to avoid repetition
                for i, response in enumerate(meaningful_responses, 1):
                    # Find the original insight for context
                    insight_context = None
                    for insight in result.insights:
                        if response in insight.reviewer_responses:
                            insight_context = insight
                            break

                    lines.extend([f"#### {i}. 回覆給 {response.reviewer}", ""])

                    # Add original comment reference if available
                    if response.original_comment:
                        # Clean and format the original comment properly
                        cleaned_comment = self._clean_original_comment(
                            response.original_comment
                        )
                        lines.extend([f"**原始評論：**", "", cleaned_comment, ""])

                    # Add technical context from insight
                    if insight_context:
                        lines.extend(
                            [
                                f"**技術領域：** {insight_context.category.value.replace('_', ' ').title()}",
                                f"**相關洞察：** {self._smart_truncate(insight_context.description, 250)}",
                                "",
                            ]
                        )

                        # Add code examples for context if available
                        if insight_context.examples:
                            lines.extend([f"**相關評論範例：**", ""])
                            for example in insight_context.examples[
                                :1
                            ]:  # Only show first example
                                lines.extend(
                                    [
                                        f"> {self._smart_truncate(example, 300)}",
                                        "",
                                    ]
                                )

                    lines.extend(
                        [
                            f"**English Response:** {response.response}",
                            "",
                            f"**Copilot 修改指令:**",
                            f"```",
                            response.copilot_instruction,
                            f"```",
                            "",
                        ]
                    )

                lines.append("")  # Extra space between commit groups

        return "\n".join(lines)

    def generate_pr_filename(
        self, result: AnalysisResult, base_dir: str = "output"
    ) -> str:
        """Generate filename based on PR information."""
        # Extract repository name (remove owner part)
        repo_parts = result.repository.split("/")
        repo_name = repo_parts[-1] if len(repo_parts) > 1 else result.repository

        # Sanitize repository name for filename
        repo_name_clean = re.sub(r"[^\w\-_]", "_", repo_name)

        # Get current date for uniqueness
        date_str = datetime.now().strftime("%Y%m%d")

        # Generate filename: repo_pr{number}_{date}_review_analysis.md
        filename = (
            f"{repo_name_clean}_pr{result.pr_number}_{date_str}_review_analysis.md"
        )

        return str(Path(base_dir) / filename)

    def save_to_file(self, content: str, file_path: str) -> bool:
        """Save formatted content to file."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Analysis result saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to {file_path}: {e}")
            return False

    def _format_timestamp(self, timestamp: str) -> str:
        """Format ISO timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return timestamp

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Smart truncation that avoids breaking words and handles Chinese text properly."""
        if len(text) <= max_length:
            return text.strip()

        # Truncate at max_length
        truncated = text[:max_length].strip()

        # Define Chinese punctuation marks
        chinese_punctuation = """。！？，、；：）】｝"'》"""

        # If the last character is not punctuation, try to find a good break point
        if truncated and truncated[-1] not in chinese_punctuation:
            # Look for the last punctuation mark within the last 50 characters
            last_punct_pos = -1
            for i in range(len(truncated) - 1, max(0, len(truncated) - 50), -1):
                if truncated[i] in chinese_punctuation:
                    last_punct_pos = i
                    break

            # If found a good break point, use it
            if last_punct_pos > 0:
                truncated = truncated[: last_punct_pos + 1]

        return truncated

    def _clean_original_comment(self, comment: str) -> str:
        """Clean and format original comment for proper Markdown display."""
        if not comment:
            return ""

        # Remove any potential outer quotes that might interfere with formatting
        comment = comment.strip()

        # If the comment contains code blocks, format them properly
        if "```" in comment:
            # Use blockquote format for comments with code blocks to avoid conflicts
            lines = comment.split("\n")
            formatted_lines = []
            for line in lines:
                # Add blockquote marker to each line
                formatted_lines.append(f"> {line}")
            return "\n".join(formatted_lines)
        else:
            # For simple text comments, use quoted format
            return f'"{comment}"'


class FormatManager:
    """Manage Markdown output format for PR analysis results."""

    def __init__(self):
        """Initialize format manager."""
        self.formatter = OutputFormatter()

    def format_result(self, result: AnalysisResult) -> str:
        """Format analysis result as Markdown."""
        return self.formatter.format_markdown_output(result)

    def save_result(self, result: AnalysisResult, output_dir: str = "output") -> str:
        """Format and save analysis result to PR-specific file."""
        try:
            # Generate PR-specific filename
            file_path = self.formatter.generate_pr_filename(result, output_dir)

            # Format content
            content = self.format_result(result)

            # Save to file
            success = self.formatter.save_to_file(content, file_path)

            if success:
                return file_path
            else:
                raise Exception("Failed to save file")

        except Exception as e:
            logger.error(f"Failed to save result: {e}")
            raise
