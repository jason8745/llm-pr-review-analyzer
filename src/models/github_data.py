"""Data models for GitHub review comments and related structures."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReviewState(Enum):
    """Enum for review states."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"


@dataclass
class ReviewComment:
    """Represents a single GitHub review comment."""

    id: int
    author: str
    content: str
    timestamp: datetime
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    commit_sha: Optional[str] = None
    review_id: Optional[int] = None
    is_bot: bool = False

    def __post_init__(self):
        """Post-initialization processing."""
        # Check if author is a bot
        if self.author.endswith("[bot]") or self.author.endswith("-bot"):
            self.is_bot = True


@dataclass
class PullRequestInfo:
    """Represents basic PR information."""

    number: int
    title: str
    author: str
    created_at: datetime
    updated_at: datetime
    state: str  # open, closed, merged
    base_branch: str
    head_branch: str
    repository: str
    url: str


@dataclass
class ReviewData:
    """Complete review data for a PR."""

    pr_info: PullRequestInfo
    comments: List[ReviewComment]
    review_states: Dict[str, ReviewState]
    total_comments: int
    unique_reviewers: int

    def __post_init__(self):
        """Calculate derived fields."""
        self.total_comments = len(self.comments)
        self.unique_reviewers = len(
            set(comment.author for comment in self.comments if not comment.is_bot)
        )

    def get_comments_by_reviewer(self) -> Dict[str, List[ReviewComment]]:
        """Group comments by reviewer, excluding bots."""
        from collections import defaultdict

        grouped = defaultdict(list)

        for comment in self.comments:
            if not comment.is_bot:
                grouped[comment.author].append(comment)

        return dict(grouped)

    def get_comments_by_file(self) -> Dict[str, List[ReviewComment]]:
        """Group comments by file path."""
        from collections import defaultdict

        grouped = defaultdict(list)

        for comment in self.comments:
            file_path = comment.file_path or "general"
            grouped[file_path].append(comment)

        return dict(grouped)
