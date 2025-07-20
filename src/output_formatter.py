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

        # Section 5: Reviewer Response Suggestions
        all_reviewer_responses = []

        for insight in result.insights:
            if hasattr(insight, "reviewer_responses") and insight.reviewer_responses:
                # Attach insight context to each response for better formatting
                for response in insight.reviewer_responses:
                    enhanced_response = {
                        "reviewer": response.reviewer,
                        "response": response.response,
                        "copilot_instruction": response.copilot_instruction,
                        "original_comment": getattr(response, "original_comment", None),
                        "insight_category": insight.category.value,
                        "insight_description": insight.description,
                        "examples": insight.examples[:2]
                        if insight.examples
                        else [],  # Include relevant code examples for context
                        "affected_files": getattr(insight, "affected_files", [])
                        if hasattr(insight, "affected_files")
                        else [],
                    }
                    all_reviewer_responses.append(enhanced_response)

        if all_reviewer_responses:
            lines.extend(["## 💬 Reviewer 回覆建議", ""])

            for i, response in enumerate(all_reviewer_responses, 1):
                lines.extend([f"### {i}. 回覆給 {response['reviewer']}", ""])

                # Add technical domain context if available
                if (
                    response["insight_category"]
                    and response["insight_category"] != "other"
                ):
                    lines.extend(
                        [
                            f"**技術領域：** {response['insight_category'].replace('_', ' ').title()}",
                            "",
                        ]
                    )

                # Add original comment reference if available
                if "original_comment" in response and response["original_comment"]:
                    lines.extend(
                        [f'**原始評論：** "{response["original_comment"]}"', ""]
                    )

                if response["insight_description"]:
                    lines.extend(
                        [
                            f"**相關洞察：** {response['insight_description'][:200]}{'...' if len(response['insight_description']) > 200 else ''}",
                            "",
                        ]
                    )

                # Add affected files reference if available
                if response["affected_files"]:
                    lines.extend(
                        [
                            f"**相關檔案：** {', '.join(response['affected_files'][:3])}",
                            "",
                        ]
                    )

                # Add code examples for context if available
                if response["examples"]:
                    lines.extend([f"**相關評論範例：**", ""])
                    for example in response["examples"]:
                        lines.extend([f"> {example}", ""])

                lines.extend(
                    [
                        f"**English Response:** {response['response']}",
                        "",
                        f"**Copilot 修改指令:**",
                        f"```",
                        response["copilot_instruction"],
                        f"```",
                        "",
                    ]
                )

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
