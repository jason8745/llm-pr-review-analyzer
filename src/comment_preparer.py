"""Data preprocessing and comment preparation for LLM analysis."""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set

from models import ReviewComment, ReviewData
from models.analysis_result import ReviewCategory
from utils import DataValidationError, get_logger

logger = get_logger(__name__)


class CommentPreparer:
    """Prepares review comments for LLM analysis."""

    def __init__(self, exclude_bots: bool = True, min_comment_length: int = 10):
        """
        Initialize comment preparer.

        Args:
            exclude_bots: Whether to exclude bot comments
            min_comment_length: Minimum comment length to include
        """
        self.exclude_bots = exclude_bots
        self.min_comment_length = min_comment_length
        self._category_keywords = self._load_category_keywords()

    def prepare_comments(self, review_data: ReviewData) -> Dict[str, any]:
        """
        Prepare comments for LLM analysis.

        Args:
            review_data: Raw review data from GitHub

        Returns:
            Dictionary with prepared data for analysis
        """
        logger.info(f"Preparing {len(review_data.comments)} comments for analysis")

        # Filter comments
        filtered_comments = self._filter_comments(review_data.comments)

        # Group comments
        grouped_data = {
            "by_reviewer": self._group_by_reviewer(filtered_comments),
            "by_file": self._group_by_file(filtered_comments),
            "by_category": self._categorize_comments(filtered_comments),
        }

        # Generate summary statistics
        stats = self._generate_statistics(filtered_comments, review_data)

        # Create structured prompt data
        prompt_data = self._create_prompt_data(grouped_data, stats)

        logger.info(f"Prepared {len(filtered_comments)} comments for analysis")

        return {
            "filtered_comments": filtered_comments,
            "grouped_data": grouped_data,
            "statistics": stats,
            "prompt_data": prompt_data,
        }

    def _filter_comments(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """Filter comments based on criteria."""
        filtered = []

        for comment in comments:
            # Skip bots if configured
            if self.exclude_bots and comment.is_bot:
                continue

            # Skip empty or very short comments
            if len(comment.content.strip()) < self.min_comment_length:
                continue

            # Skip common non-substantive comments
            if self._is_non_substantive(comment.content):
                continue

            filtered.append(comment)

        return filtered

    def _is_non_substantive(self, content: str) -> bool:
        """Check if comment is non-substantive (e.g., just 'LGTM')."""
        non_substantive_patterns = [
            r"^lgtm\.?$",
            r"^looks good to me\.?$",
            r"^approved\.?$",
            r"^👍+$",
            r"^✅+$",
            r"^:\+1:+$",
            r"^good\.?$",
            r"^nice\.?$",
            r"^\+1\.?$",
        ]

        content_lower = content.lower().strip()

        for pattern in non_substantive_patterns:
            if re.match(pattern, content_lower):
                return True

        return False

    def _group_by_reviewer(
        self, comments: List[ReviewComment]
    ) -> Dict[str, List[ReviewComment]]:
        """Group comments by reviewer."""
        grouped = defaultdict(list)

        for comment in comments:
            grouped[comment.author].append(comment)

        return dict(grouped)

    def _group_by_file(
        self, comments: List[ReviewComment]
    ) -> Dict[str, List[ReviewComment]]:
        """Group comments by file path."""
        grouped = defaultdict(list)

        for comment in comments:
            file_path = comment.file_path or "general"
            grouped[file_path].append(comment)

        return dict(grouped)

    def _categorize_comments(
        self, comments: List[ReviewComment]
    ) -> Dict[ReviewCategory, List[ReviewComment]]:
        """Categorize comments based on content analysis."""
        categorized = defaultdict(list)

        for comment in comments:
            categories = self._detect_categories(comment.content)

            if not categories:
                categories = [ReviewCategory.OTHER]

            for category in categories:
                categorized[category].append(comment)

        return dict(categorized)

    def _detect_categories(self, content: str) -> List[ReviewCategory]:
        """Detect review categories based on keywords."""
        content_lower = content.lower()
        detected_categories = []

        for category, keywords in self._category_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    detected_categories.append(category)
                    break  # One match per category is enough

        return detected_categories

    def _generate_statistics(
        self, comments: List[ReviewComment], review_data: ReviewData
    ) -> Dict[str, any]:
        """Generate summary statistics."""
        reviewer_comment_counts = Counter(comment.author for comment in comments)
        file_comment_counts = Counter(
            comment.file_path or "general" for comment in comments
        )

        # Calculate average comment length
        comment_lengths = [len(comment.content) for comment in comments]
        avg_length = (
            sum(comment_lengths) / len(comment_lengths) if comment_lengths else 0
        )

        return {
            "total_comments": len(comments),
            "unique_reviewers": len(set(comment.author for comment in comments)),
            "comments_per_reviewer": dict(reviewer_comment_counts),
            "comments_per_file": dict(file_comment_counts),
            "average_comment_length": round(avg_length, 2),
            "pr_info": {
                "number": review_data.pr_info.number,
                "title": review_data.pr_info.title,
                "repository": review_data.pr_info.repository,
                "author": review_data.pr_info.author,
            },
        }

    def _create_prompt_data(self, grouped_data: Dict, stats: Dict) -> str:
        """Create structured data for LLM prompt."""
        prompt_parts = []

        # Add PR context
        prompt_parts.append(f"# PR Analysis Context")
        prompt_parts.append(f"Repository: {stats['pr_info']['repository']}")
        prompt_parts.append(
            f"PR #{stats['pr_info']['number']}: {stats['pr_info']['title']}"
        )
        prompt_parts.append(f"Total Comments: {stats['total_comments']}")
        prompt_parts.append(f"Unique Reviewers: {stats['unique_reviewers']}")
        prompt_parts.append("")

        # Add comments by reviewer
        prompt_parts.append("## Comments by Reviewer")
        for reviewer, comments in grouped_data["by_reviewer"].items():
            prompt_parts.append(f"### {reviewer} ({len(comments)} comments)")
            for i, comment in enumerate(comments[:5], 1):  # Limit to top 5 per reviewer
                prompt_parts.append(f"{i}. {comment.content[:200]}...")
            if len(comments) > 5:
                prompt_parts.append(f"... and {len(comments) - 5} more comments")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def _load_category_keywords(self) -> Dict[ReviewCategory, List[str]]:
        """Load keyword mappings for categorization."""
        return {
            ReviewCategory.ARCHITECTURE: [
                "architecture",
                "design",
                "structure",
                "pattern",
                "refactor",
                "coupling",
                "cohesion",
                "separation",
                "abstraction",
                "interface",
            ],
            ReviewCategory.CODE_STYLE: [
                "style",
                "formatting",
                "convention",
                "naming",
                "indentation",
                "spacing",
                "line length",
                "readability",
                "clean code",
            ],
            ReviewCategory.PERFORMANCE: [
                "performance",
                "speed",
                "slow",
                "optimization",
                "efficient",
                "memory",
                "cpu",
                "bottleneck",
                "cache",
                "algorithm",
            ],
            ReviewCategory.SECURITY: [
                "security",
                "vulnerability",
                "exploit",
                "authentication",
                "authorization",
                "sanitize",
                "validation",
                "injection",
                "xss",
            ],
            ReviewCategory.TESTING: [
                "test",
                "testing",
                "unit test",
                "integration",
                "coverage",
                "mock",
                "assertion",
                "testcase",
                "pytest",
                "unittest",
            ],
            ReviewCategory.DOCUMENTATION: [
                "documentation",
                "comment",
                "docstring",
                "readme",
                "docs",
                "explain",
                "clarify",
                "description",
                "example",
            ],
            ReviewCategory.NAMING: [
                "naming",
                "variable name",
                "function name",
                "class name",
                "descriptive",
                "meaningful",
                "confusing name",
                "rename",
            ],
            ReviewCategory.ERROR_HANDLING: [
                "error",
                "exception",
                "try",
                "catch",
                "finally",
                "handling",
                "error handling",
                "exception handling",
                "graceful",
            ],
            ReviewCategory.MAINTAINABILITY: [
                "maintainable",
                "maintenance",
                "readable",
                "complexity",
                "simple",
                "complicated",
                "understand",
                "clear",
            ],
        }
