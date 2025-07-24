"""Data models for LLM analysis results with enhanced knowledge extraction."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from utils.logging_config import get_logger


class ReviewCategory(Enum):
    """Categories of review feedback."""

    ARCHITECTURE = "architecture"
    CODE_STYLE = "code_style"
    PERFORMANCE = "performance"
    SECURITY = "security"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    NAMING = "naming"
    ERROR_HANDLING = "error_handling"
    MAINTAINABILITY = "maintainability"
    BUSINESS_LOGIC = "business_logic"
    API_DESIGN = "api_design"
    DATA_HANDLING = "data_handling"
    USER_EXPERIENCE = "user_experience"
    OTHER = "other"


class Severity(Enum):
    """Severity levels for review insights."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ReviewerKnowledgeInsight:
    """Represents deep knowledge insight from a reviewer."""

    technical_knowledge: str = ""
    experience_lessons: str = ""
    design_philosophy: str = ""
    best_practices: List[str] = field(default_factory=list)
    common_pitfalls: List[str] = field(default_factory=list)


@dataclass
class ReviewerResponse:
    """Represents a response to a reviewer's comment with Copilot instruction."""

    reviewer: str
    response: str  # English response under 30 words
    copilot_instruction: str  # Specific instruction for Copilot agent
    commit_group: Optional[str] = None  # Logical grouping identifier
    suggested_commit_message: Optional[str] = None  # Suggested commit message

    # Enhanced context information
    original_comment: Optional[str] = None  # The original comment text
    file_path: Optional[str] = None  # File where the comment was made
    line_number: Optional[int] = None  # Line number of the comment
    comment_url: Optional[str] = None  # Direct URL to the comment


@dataclass
class ReviewInsight:
    """Represents a single insight from review analysis with enhanced learning focus."""

    category: ReviewCategory
    description: str
    frequency: int
    severity: Severity
    examples: List[str] = field(default_factory=list)
    reviewers_mentioned: List[str] = field(default_factory=list)

    # Enhanced knowledge extraction fields
    reviewer_insights: Optional[ReviewerKnowledgeInsight] = None
    immediate_actions: List[str] = field(
        default_factory=list
    )  # Simplified from learning_opportunities
    reviewer_responses: List[ReviewerResponse] = field(default_factory=list)

    @staticmethod
    def _get_logger():
        """Get logger instance."""
        return get_logger(__name__)

    @classmethod
    def from_llm_response(cls, data: Any) -> "ReviewInsight":
        """Create ReviewInsight from LLM JSON response."""
        # Handle case where data is not a dict (e.g., it's a list or None)
        if not isinstance(data, dict):
            logger = cls._get_logger()
            logger.warning(f"Expected dict but got {type(data)}: {data}")
            # Return a minimal ReviewInsight with error info
            return cls(
                category=ReviewCategory.OTHER,
                description="Failed to parse LLM response - received non-dict data",
                frequency=1,
                severity=Severity.LOW,
                immediate_actions=["Review LLM response format"],
                reviewer_responses=[],
            )

        # Basic fields
        category = ReviewCategory(data.get("category", "other"))
        description = data.get("description", "")
        frequency = data.get("frequency", 1)
        severity = Severity(data.get("severity", "medium"))

        # Enhanced knowledge fields
        reviewer_insights = None
        if "reviewer_insights" in data:
            ri_data = data["reviewer_insights"]
            reviewer_insights = ReviewerKnowledgeInsight(
                technical_knowledge=ri_data.get("technical_knowledge", ""),
                experience_lessons=ri_data.get("experience_lessons", ""),
                design_philosophy=ri_data.get("design_philosophy", ""),
                best_practices=ri_data.get("best_practices", []),
                common_pitfalls=ri_data.get("common_pitfalls", []),
            )

        # Extract immediate actions from various sources
        immediate_actions = []
        if "learning_opportunities" in data:
            lo_data = data["learning_opportunities"]
            immediate_actions.extend(lo_data.get("immediate_actions", []))

        if "actionable_guidance" in data:
            ag_data = data["actionable_guidance"]
            immediate_actions.extend(ag_data.get("immediate_actions", []))

        # Parse reviewer responses
        reviewer_responses = []
        if "reviewer_responses" in data:
            for resp_data in data["reviewer_responses"]:
                reviewer_responses.append(
                    ReviewerResponse(
                        reviewer=resp_data.get("reviewer", ""),
                        response=resp_data.get("response", ""),
                        copilot_instruction=resp_data.get("copilot_instruction", ""),
                        commit_group=resp_data.get("commit_group", None),
                        suggested_commit_message=resp_data.get(
                            "suggested_commit_message", None
                        ),
                        original_comment=resp_data.get("original_comment", None),
                    )
                )

        return cls(
            category=category,
            description=description,
            frequency=frequency,
            severity=severity,
            examples=data.get("examples", []),
            reviewers_mentioned=data.get("reviewers_mentioned", []),
            reviewer_insights=reviewer_insights,
            immediate_actions=immediate_actions,
            reviewer_responses=reviewer_responses,
        )


@dataclass
class ReviewerProfile:
    """Profile of a reviewer's focus areas with enhanced mentoring perspective."""

    reviewer_name: str
    total_comments: int
    top_categories: List[ReviewCategory]
    average_comment_length: float
    focus_areas: Dict[ReviewCategory, int]

    # Enhanced mentoring analysis
    mentoring_style: Optional[str] = None  # detailed, concise, directive, collaborative
    knowledge_domains: List[str] = field(
        default_factory=list
    )  # specific areas of expertise
    teaching_approach: Optional[str] = None  # explanation, example, reference, practice


@dataclass
class AnalysisResult:
    """Complete analysis result for a PR with learning-focused insights."""

    pr_number: int
    repository: str
    analysis_timestamp: str
    insights: List[ReviewInsight]
    reviewer_profiles: List[ReviewerProfile]

    # Core output fields used in the 5-section format
    key_knowledge_insights: List[str] = field(default_factory=list)
    learning_opportunities: Dict[str, List[str]] = field(default_factory=dict)
    mentoring_insights: List[str] = field(default_factory=list)
    valuable_insights: Optional[Dict[str, List[str]]] = None

    def get_insights_by_category(self) -> Dict[ReviewCategory, List[ReviewInsight]]:
        """Group insights by category."""
        from collections import defaultdict

        grouped = defaultdict(list)

        for insight in self.insights:
            grouped[insight.category].append(insight)

        return dict(grouped)

    def get_high_priority_insights(self) -> List[ReviewInsight]:
        """Get only high severity insights."""
        return [
            insight for insight in self.insights if insight.severity == Severity.HIGH
        ]

    def get_learning_focused_insights(self) -> List[ReviewInsight]:
        """Get insights with rich learning content."""
        return [
            insight
            for insight in self.insights
            if insight.reviewer_insights
            or insight.immediate_actions
            or insight.reviewer_responses
        ]

    def get_reviewer_responses_by_commit_group(
        self,
    ) -> Dict[str, List[ReviewerResponse]]:
        """Group all reviewer responses by their commit groups, removing duplicates."""
        from collections import defaultdict

        grouped_responses = defaultdict(list)
        seen_responses = set()  # Track seen responses to avoid duplicates

        for insight in self.insights:
            for response in insight.reviewer_responses:
                # Create a unique key for this response to detect duplicates
                response_key = (
                    response.reviewer,
                    response.original_comment,
                    response.commit_group,
                )

                # Skip if we've already seen this exact response
                if response_key in seen_responses:
                    continue

                seen_responses.add(response_key)

                if response.commit_group:
                    grouped_responses[response.commit_group].append(response)
                else:
                    # Default group for ungrouped responses
                    grouped_responses["general"].append(response)

        return dict(grouped_responses)

    def get_suggested_commit_messages(self) -> Dict[str, str]:
        """Get unique suggested commit messages by commit group."""
        commit_messages = {}

        for insight in self.insights:
            for response in insight.reviewer_responses:
                if response.commit_group and response.suggested_commit_message:
                    # Use the first commit message found for each group
                    if response.commit_group not in commit_messages:
                        commit_messages[response.commit_group] = (
                            response.suggested_commit_message
                        )

        return commit_messages
