"""Reviewer profile builder."""

from collections import Counter
from typing import Dict, List, Optional

from models.analysis_result import ReviewCategory, ReviewerProfile
from utils import get_logger

logger = get_logger(__name__)


class ProfileBuilder:
    """Build reviewer profiles from comment data."""

    @staticmethod
    def build_reviewer_profiles(
        reviewer_comments: Dict[str, List],
    ) -> List[ReviewerProfile]:
        """Build profiles for all reviewers."""
        profiles = []

        for reviewer, comments in reviewer_comments.items():
            if len(comments) >= 1:  # Analyze any reviewer with comments
                try:
                    profile = ProfileBuilder.create_reviewer_profile(reviewer, comments)
                    if profile:
                        profiles.append(profile)
                except Exception as e:
                    logger.warning(f"Failed to analyze reviewer {reviewer}: {e}")

        return profiles

    @staticmethod
    def create_reviewer_profile(
        reviewer: str, comments: List
    ) -> Optional[ReviewerProfile]:
        """Create a profile for a specific reviewer."""
        comment_count = len(comments)
        avg_length = sum(len(c.content) for c in comments) / comment_count

        # Analyze comment categories based on content keywords
        category_counts = ProfileBuilder.categorize_comments(comments)

        # Get top categories (at least 1, max 3)
        top_categories = [
            cat for cat, count in category_counts.most_common(3) if count > 0
        ]
        if not top_categories:
            top_categories = [ReviewCategory.OTHER]

        # Create focus areas dict
        focus_areas = dict(category_counts.most_common())

        return ReviewerProfile(
            reviewer_name=reviewer,
            total_comments=comment_count,
            top_categories=top_categories,
            average_comment_length=round(avg_length, 1),
            focus_areas=focus_areas,
        )

    @staticmethod
    def categorize_comments(comments: List) -> Counter:
        """Categorize comments based on content keywords."""
        category_counts = Counter()

        # Define keyword mappings
        keyword_categories = {
            ReviewCategory.MAINTAINABILITY: [
                "config",
                "configuration",
                "setting",
                "maintain",
                "refactor",
                "organize",
            ],
            ReviewCategory.DOCUMENTATION: [
                "document",
                "readme",
                "comment",
                "explain",
                "clarify",
            ],
            ReviewCategory.ARCHITECTURE: [
                "architecture",
                "design",
                "structure",
                "pattern",
                "tool",
                "build",
            ],
            ReviewCategory.CODE_STYLE: [
                "style",
                "format",
                "naming",
                "convention",
                "clean",
            ],
            ReviewCategory.ERROR_HANDLING: [
                "error",
                "exception",
                "handle",
                "graceful",
                "shutdown",
            ],
            ReviewCategory.TESTING: ["test", "testing", "coverage", "spec"],
            ReviewCategory.PERFORMANCE: [
                "performance",
                "optimize",
                "efficient",
                "fast",
                "slow",
            ],
            ReviewCategory.SECURITY: [
                "security",
                "auth",
                "permission",
                "validate",
                "sanitize",
            ],
        }

        for comment in comments:
            content_lower = comment.content.lower()
            categorized = False

            # Check each category's keywords
            for category, keywords in keyword_categories.items():
                if any(word in content_lower for word in keywords):
                    category_counts[category] += 1
                    categorized = True
                    break

            # Default to OTHER if no category matched
            if not categorized:
                category_counts[ReviewCategory.OTHER] += 1

        return category_counts
