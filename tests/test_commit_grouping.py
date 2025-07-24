"""Tests for commit grouping functionality in analysis results."""

from datetime import datetime

import pytest

from models.analysis_result import (
    AnalysisResult,
    ReviewCategory,
    ReviewerResponse,
    ReviewInsight,
    Severity,
)


class TestCommitGrouping:
    """Test commit grouping functionality in analysis results."""

    def create_sample_reviewer_response(
        self,
        reviewer: str,
        commit_group: str = None,
        suggested_commit_message: str = None,
    ) -> ReviewerResponse:
        """Create a sample ReviewerResponse for testing."""
        return ReviewerResponse(
            reviewer=reviewer,
            response="Thanks for the feedback!",
            copilot_instruction="First analyze: What are the current patterns? After analysis, if needed: Implement the suggestion.",
            commit_group=commit_group,
            suggested_commit_message=suggested_commit_message,
            original_comment="This needs improvement",
        )

    def create_sample_analysis_result(self) -> AnalysisResult:
        """Create a sample AnalysisResult with various commit groups."""
        # Create insights with different commit groups
        insight1 = ReviewInsight(
            category=ReviewCategory.ERROR_HANDLING,
            description="Error handling improvements",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[
                self.create_sample_reviewer_response(
                    "alice",
                    "error-handling",
                    "feat: improve error handling in user service",
                ),
                self.create_sample_reviewer_response(
                    "bob",
                    "error-handling",
                    "feat: add try-catch blocks for database operations",
                ),
            ],
        )

        insight2 = ReviewInsight(
            category=ReviewCategory.CODE_STYLE,
            description="Code style improvements",
            frequency=1,
            severity=Severity.MEDIUM,
            reviewer_responses=[
                self.create_sample_reviewer_response(
                    "charlie",
                    "code-style",
                    "style: apply consistent formatting and naming",
                ),
            ],
        )

        insight3 = ReviewInsight(
            category=ReviewCategory.PERFORMANCE,
            description="Performance optimization",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[
                self.create_sample_reviewer_response(
                    "diana",
                    "performance-optimization",
                    "perf: optimize database queries and caching",
                ),
            ],
        )

        # One response without commit group (should go to "general")
        insight4 = ReviewInsight(
            category=ReviewCategory.DOCUMENTATION,
            description="Documentation update",
            frequency=1,
            severity=Severity.LOW,
            reviewer_responses=[
                self.create_sample_reviewer_response("eve")  # No commit group
            ],
        )

        return AnalysisResult(
            pr_number=123,
            repository="test/repo",
            analysis_timestamp=datetime.now().isoformat(),
            insights=[insight1, insight2, insight3, insight4],
            reviewer_profiles=[],
        )

    def test_get_reviewer_responses_by_commit_group(self):
        """Test grouping reviewer responses by commit group."""
        result = self.create_sample_analysis_result()
        grouped_responses = result.get_reviewer_responses_by_commit_group()

        # Check that we have the expected groups
        expected_groups = {
            "error-handling",
            "code-style",
            "performance-optimization",
            "general",
        }
        assert set(grouped_responses.keys()) == expected_groups

        # Check error-handling group has 2 responses
        assert len(grouped_responses["error-handling"]) == 2
        error_handling_reviewers = [
            r.reviewer for r in grouped_responses["error-handling"]
        ]
        assert "alice" in error_handling_reviewers
        assert "bob" in error_handling_reviewers

        # Check code-style group has 1 response
        assert len(grouped_responses["code-style"]) == 1
        assert grouped_responses["code-style"][0].reviewer == "charlie"

        # Check performance-optimization group has 1 response
        assert len(grouped_responses["performance-optimization"]) == 1
        assert grouped_responses["performance-optimization"][0].reviewer == "diana"

        # Check general group has the ungrouped response
        assert len(grouped_responses["general"]) == 1
        assert grouped_responses["general"][0].reviewer == "eve"

    def test_get_suggested_commit_messages(self):
        """Test extracting suggested commit messages by group."""
        result = self.create_sample_analysis_result()
        commit_messages = result.get_suggested_commit_messages()

        # Check that we have commit messages for the expected groups
        expected_groups = {"error-handling", "code-style", "performance-optimization"}
        assert set(commit_messages.keys()) == expected_groups

        # Check specific commit messages
        assert (
            commit_messages["error-handling"]
            == "feat: improve error handling in user service"
        )
        assert (
            commit_messages["code-style"]
            == "style: apply consistent formatting and naming"
        )
        assert (
            commit_messages["performance-optimization"]
            == "perf: optimize database queries and caching"
        )

        # General group should not have a commit message since the response didn't specify one
        assert "general" not in commit_messages

    def test_commit_group_deduplication(self):
        """Test that duplicate commit messages are handled correctly."""
        # Create an insight with multiple responses having different commit messages for the same group
        insight = ReviewInsight(
            category=ReviewCategory.ERROR_HANDLING,
            description="Error handling improvements",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[
                self.create_sample_reviewer_response(
                    "alice",
                    "error-handling",
                    "feat: improve error handling in user service",
                ),
                self.create_sample_reviewer_response(
                    "bob",
                    "error-handling",
                    "feat: add comprehensive error handling",  # Different message
                ),
            ],
        )

        result = AnalysisResult(
            pr_number=123,
            repository="test/repo",
            analysis_timestamp=datetime.now().isoformat(),
            insights=[insight],
            reviewer_profiles=[],
        )

        commit_messages = result.get_suggested_commit_messages()

        # Should use the first commit message found for the group
        assert (
            commit_messages["error-handling"]
            == "feat: improve error handling in user service"
        )

    def test_empty_insights(self):
        """Test behavior with empty insights."""
        result = AnalysisResult(
            pr_number=123,
            repository="test/repo",
            analysis_timestamp=datetime.now().isoformat(),
            insights=[],
            reviewer_profiles=[],
        )

        grouped_responses = result.get_reviewer_responses_by_commit_group()
        commit_messages = result.get_suggested_commit_messages()

        assert grouped_responses == {}
        assert commit_messages == {}

    def test_insights_without_reviewer_responses(self):
        """Test behavior with insights that have no reviewer responses."""
        insight = ReviewInsight(
            category=ReviewCategory.ERROR_HANDLING,
            description="Error handling improvements",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[],  # No responses
        )

        result = AnalysisResult(
            pr_number=123,
            repository="test/repo",
            analysis_timestamp=datetime.now().isoformat(),
            insights=[insight],
            reviewer_profiles=[],
        )

        grouped_responses = result.get_reviewer_responses_by_commit_group()
        commit_messages = result.get_suggested_commit_messages()

        assert grouped_responses == {}
        assert commit_messages == {}

    def test_duplicate_response_removal(self):
        """Test that duplicate reviewer responses are removed."""
        # Create the same response for the same comment
        duplicate_response = self.create_sample_reviewer_response(
            "alice", "error-handling", "feat: improve error handling"
        )
        duplicate_response.original_comment = "This needs better error handling"

        # Create two insights with the same response (simulating the duplication issue)
        insight1 = ReviewInsight(
            category=ReviewCategory.ERROR_HANDLING,
            description="Error handling improvements",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[duplicate_response],
        )

        insight2 = ReviewInsight(
            category=ReviewCategory.ARCHITECTURE,
            description="Architecture improvements",
            frequency=1,
            severity=Severity.HIGH,
            reviewer_responses=[duplicate_response],  # Same response
        )

        result = AnalysisResult(
            pr_number=123,
            repository="test/repo",
            analysis_timestamp=datetime.now().isoformat(),
            insights=[insight1, insight2],
            reviewer_profiles=[],
        )

        grouped_responses = result.get_reviewer_responses_by_commit_group()

        # Should only have one response in the error-handling group, not two
        assert len(grouped_responses["error-handling"]) == 1
        assert grouped_responses["error-handling"][0].reviewer == "alice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
