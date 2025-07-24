"""Utility functions for LLM analysis chains."""

import time
from typing import Any, Dict, List

from .exceptions import LLMAnalysisError
from .logging_config import get_logger

logger = get_logger(__name__)


class ChainExecutor:
    """Utility class for executing LLM chains with retry logic."""

    def __init__(self, retry_count: int = 3):
        """Initialize chain executor with retry configuration."""
        self.retry_count = retry_count

    def execute_with_retry(self, chain, input_data: Dict) -> Dict:
        """Execute chain with retry logic and exponential backoff."""
        for attempt in range(self.retry_count):
            try:
                logger.info(f"Executing chain attempt {attempt + 1}/{self.retry_count}")
                logger.debug(f"Input data keys: {list(input_data.keys())}")

                result = chain.invoke(input_data)

                logger.info(f"Chain execution successful on attempt {attempt + 1}")
                logger.debug(
                    f"Result type: {type(result)}, length: {len(str(result)) if result else 0}"
                )

                # Log if result is empty or None
                if not result:
                    logger.warning(f"Chain returned empty result: {result}")
                elif isinstance(result, str) and not result.strip():
                    logger.warning(f"Chain returned empty string")

                return result
            except Exception as e:
                logger.warning(f"Chain execution attempt {attempt + 1} failed: {e}")
                logger.debug(f"Exception type: {type(e)}, details: {str(e)}")

                if attempt < self.retry_count - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)  # Exponential backoff
                else:
                    logger.error(f"All {self.retry_count} attempts failed")
                    raise LLMAnalysisError(
                        f"Chain execution failed after {self.retry_count} attempts: {e}"
                    )


class ReviewerCommentProcessor:
    """Utility class for processing and filtering reviewer comments."""

    @staticmethod
    def separate_reviewer_comments(
        comments_by_author: Dict[str, List], pr_creator: str
    ) -> Dict[str, List]:
        """Separate reviewer comments from PR creator responses."""
        reviewer_comments = {}

        for author, comments in comments_by_author.items():
            if author != pr_creator:  # Only include actual reviewers
                reviewer_comments[author] = comments

        logger.info(
            f"Separated comments: {len(reviewer_comments)} reviewers, excluding PR creator '{pr_creator}'"
        )
        return reviewer_comments

    @staticmethod
    def categorize_reviewer_comments(
        categorized_comments: Dict, pr_creator: str
    ) -> Dict:
        """Filter categorized comments to exclude PR creator responses."""
        reviewer_categories = {}

        for category, comments in categorized_comments.items():
            reviewer_only_comments = [c for c in comments if c.author != pr_creator]
            if reviewer_only_comments:
                reviewer_categories[category] = reviewer_only_comments

        return reviewer_categories
