"""Tests for comment preparation functionality."""

from unittest.mock import Mock

import pytest

from comment_preparer import CommentPreparer
from models import ReviewCategory


class TestCommentPreparer:
    """Test comment preparation functionality."""

    def test_filter_comments_excludes_bots(self, sample_review_data):
        """Test that bot comments are excluded when configured."""
        preparer = CommentPreparer(exclude_bots=True)

        # Should exclude the dependabot comment
        filtered = preparer._filter_comments(sample_review_data.comments)

        authors = [comment.author for comment in filtered]
        assert "dependabot[bot]" not in authors
        assert len(filtered) == 2

    def test_filter_comments_includes_bots_when_configured(self, sample_review_data):
        """Test that bot comments are included when configured."""
        preparer = CommentPreparer(exclude_bots=False)

        filtered = preparer._filter_comments(sample_review_data.comments)

        authors = [comment.author for comment in filtered]
        assert "dependabot[bot]" in authors
        assert len(filtered) == 3

    def test_filter_comments_min_length(self, sample_review_data):
        """Test minimum comment length filtering."""
        # Add a very short comment
        sample_review_data.comments.append(
            Mock(author="test", content="ok", is_bot=False)
        )

        preparer = CommentPreparer(min_comment_length=10)
        filtered = preparer._filter_comments(sample_review_data.comments)

        # Should exclude the short "ok" comment
        contents = [comment.content for comment in filtered]
        assert "ok" not in contents

    def test_is_non_substantive(self):
        """Test non-substantive comment detection."""
        preparer = CommentPreparer()

        # These should be considered non-substantive
        non_substantive = ["LGTM", "lgtm.", "Looks good to me", "👍", "approved"]
        for comment in non_substantive:
            assert preparer._is_non_substantive(comment)

        # These should be considered substantive
        substantive = [
            "Please add error handling here.",
            "Consider using a more descriptive variable name.",
            "This implementation has a potential race condition.",
        ]
        for comment in substantive:
            assert not preparer._is_non_substantive(comment)

    def test_group_by_reviewer(self, sample_review_data):
        """Test grouping comments by reviewer."""
        preparer = CommentPreparer()
        grouped = preparer._group_by_reviewer(sample_review_data.comments)

        assert "reviewer1" in grouped
        assert "reviewer2" in grouped
        assert len(grouped["reviewer1"]) == 1
        assert len(grouped["reviewer2"]) == 1

    def test_group_by_file(self, sample_review_data):
        """Test grouping comments by file."""
        preparer = CommentPreparer()
        grouped = preparer._group_by_file(sample_review_data.comments)

        assert "src/main.py" in grouped
        assert "src/utils.py" in grouped
        assert "general" in grouped  # For comments without file_path

    def test_detect_categories(self):
        """Test category detection from comment content."""
        preparer = CommentPreparer()

        test_cases = [
            ("Please add error handling here.", [ReviewCategory.ERROR_HANDLING]),
            (
                "This function could be optimized for performance.",
                [ReviewCategory.PERFORMANCE],
            ),
            (
                "Consider using a more descriptive variable name.",
                [ReviewCategory.NAMING],
            ),
            ("Add unit tests for this function.", [ReviewCategory.TESTING]),
            ("The architecture could be improved.", [ReviewCategory.ARCHITECTURE]),
        ]

        for content, expected_categories in test_cases:
            detected = preparer._detect_categories(content)
            for category in expected_categories:
                assert category in detected

    def test_prepare_comments_integration(self, sample_review_data):
        """Test the complete comment preparation process."""
        preparer = CommentPreparer(exclude_bots=True)
        result = preparer.prepare_comments(sample_review_data)

        # Check that all expected keys are present
        expected_keys = [
            "filtered_comments",
            "grouped_data",
            "statistics",
            "prompt_data",
        ]
        for key in expected_keys:
            assert key in result

        # Check statistics
        stats = result["statistics"]
        assert stats["total_comments"] == 2  # Excluding bot
        assert stats["unique_reviewers"] == 2
        assert "pr_info" in stats

        # Check grouped data
        grouped = result["grouped_data"]
        assert "by_reviewer" in grouped
        assert "by_file" in grouped
        assert "by_category" in grouped
