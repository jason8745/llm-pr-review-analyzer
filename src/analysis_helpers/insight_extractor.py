"""Deep knowledge extraction and learning opportunity identification tool - Cleaned version."""

from typing import Any, Dict, List

from models.analysis_result import ReviewInsight
from utils import get_logger

logger = get_logger(__name__)


class InsightExtractor:
    """Extract deep knowledge and learning opportunities from reviewer insights."""

    @staticmethod
    def extract_knowledge_insights(insights: List[ReviewInsight]) -> List[str]:
        """Extract core knowledge insights, focusing on professional knowledge shared by reviewers."""
        knowledge_insights = []

        # Sort by knowledge value and learning importance
        sorted_insights = sorted(
            insights,
            key=lambda x: InsightExtractor._calculate_learning_value(x),
            reverse=True,
        )

        for insight in sorted_insights[:10]:  # Take top 10 most valuable insights
            # Extract knowledge points
            if hasattr(insight, "reviewer_insights") and insight.reviewer_insights:
                formatted_insight = InsightExtractor._format_knowledge_insight(insight)
                if formatted_insight:
                    knowledge_insights.append(formatted_insight)
            else:
                # Fallback for legacy format
                legacy_insight = InsightExtractor._extract_legacy_insight(insight)
                if legacy_insight:
                    knowledge_insights.append(legacy_insight)

        return knowledge_insights

    @staticmethod
    def extract_learning_opportunities(
        insights: List[ReviewInsight],
    ) -> Dict[str, List[str]]:
        """Identify specific learning opportunities and growth directions."""
        opportunities = {
            "immediate_actions": [],
        }

        for insight in insights:
            # Extract from simplified immediate_actions field
            if hasattr(insight, "immediate_actions") and insight.immediate_actions:
                opportunities["immediate_actions"].extend(insight.immediate_actions)

        # Remove duplicates and limit quantity
        for key in opportunities:
            opportunities[key] = list(set(opportunities[key]))[:10]

        return opportunities

    @staticmethod
    def extract_mentoring_insights(insights: List[ReviewInsight]) -> List[str]:
        """Extract mentor-level technical insights, focusing on deep technical guidance."""
        mentoring_insights = []

        for insight in insights:
            if hasattr(insight, "reviewer_insights") and insight.reviewer_insights:
                reviewer_data = insight.reviewer_insights

                # Combine technical knowledge and experience lessons
                technical_knowledge = getattr(reviewer_data, "technical_knowledge", "")
                experience_lessons = getattr(reviewer_data, "experience_lessons", "")
                design_philosophy = getattr(reviewer_data, "design_philosophy", "")

                # Format mentor-level insight
                formatted_insight = InsightExtractor._format_mentoring_insight(
                    insight.category.value,
                    technical_knowledge,
                    experience_lessons,
                    design_philosophy,
                )
                if formatted_insight:
                    mentoring_insights.append(formatted_insight)

        return mentoring_insights[:10]  # Maximum 10 key insights

    @staticmethod
    def extract_valuable_insights(
        insights: List[ReviewInsight], prepared_data: Dict
    ) -> Dict[str, List[str]]:
        """Extract valuable insights for style formation from analysis results."""
        valuable_insights = {
            "style_forming_comments": [],
            "development_philosophy": [],
            "professional_habits": [],
        }

        for insight in insights:
            # Extract from new structured format
            if hasattr(insight, "actionable_guidance") and insight.actionable_guidance:
                if hasattr(insight.actionable_guidance, "valuable_comments"):
                    valuable_insights["style_forming_comments"].extend(
                        insight.actionable_guidance.valuable_comments or []
                    )

            if hasattr(insight, "reviewer_insights") and insight.reviewer_insights:
                if hasattr(insight.reviewer_insights, "design_philosophy"):
                    philosophy = insight.reviewer_insights.design_philosophy
                    if philosophy and len(philosophy.strip()) > 10:
                        valuable_insights["development_philosophy"].append(philosophy)

                if hasattr(insight.reviewer_insights, "best_practices"):
                    practices = insight.reviewer_insights.best_practices or []
                    valuable_insights["professional_habits"].extend(practices)

        # If no valuable comments found from new fields, use fallback from existing patterns
        if not any(valuable_insights.values()):
            for insight in insights:
                if hasattr(insight, "reviewer_insights") and insight.reviewer_insights:
                    # Use technical knowledge as style forming insight
                    tech_knowledge = getattr(
                        insight.reviewer_insights, "technical_knowledge", ""
                    )
                    if tech_knowledge and len(tech_knowledge.strip()) > 20:
                        valuable_insights["style_forming_comments"].append(
                            f"reviewer 展現{insight.category.value.replace('_', ' ')}的深入理解，{tech_knowledge[:200]}{'...' if len(tech_knowledge) > 200 else ''}"
                        )

        # Clean up and deduplicate
        for key in valuable_insights:
            valuable_insights[key] = list(set(valuable_insights[key]))[:10]

        return valuable_insights

    @staticmethod
    def _calculate_learning_value(insight: ReviewInsight) -> float:
        """Calculate learning value score for insight."""
        base_score = 0

        # Frequency weight
        base_score += insight.frequency * 2

        # Severity weight
        severity_weights = {"high": 5, "medium": 3, "low": 1}
        base_score += severity_weights.get(insight.severity.value, 0)

        # Knowledge density weight (description length and depth)
        if len(insight.description) > 200:
            base_score += 2

        # Reviewer diversity weight
        base_score += len(insight.reviewers_mentioned) * 1.5

        return base_score

    @staticmethod
    def _format_knowledge_insight(insight: ReviewInsight) -> str:
        """Format knowledge insight as readable learning point."""
        try:
            category = insight.category.value.replace("_", " ").title()
            knowledge_area = category

            # Try to get technical knowledge
            if hasattr(insight, "reviewer_insights") and insight.reviewer_insights:
                tech_knowledge = getattr(
                    insight.reviewer_insights, "technical_knowledge", ""
                )
                experience = getattr(
                    insight.reviewer_insights, "experience_lessons", ""
                )

                if tech_knowledge and len(tech_knowledge.strip()) > 20:
                    return f"{knowledge_area}: {tech_knowledge[:150]}{'...' if len(tech_knowledge) > 150 else ''}"
                elif experience and len(experience.strip()) > 20:
                    return f"{knowledge_area}: {experience[:150]}{'...' if len(experience) > 150 else ''}"

            # Fallback to description
            return f"{knowledge_area}: {insight.description[:150]}{'...' if len(insight.description) > 150 else ''}"

        except Exception as e:
            logger.warning(f"Error formatting knowledge insight: {e}")
            return None

    @staticmethod
    def _extract_legacy_insight(insight: ReviewInsight) -> str:
        """Handle legacy format insight extraction."""
        category = insight.category.value.replace("_", " ").title()
        return f"{category}: {insight.description[:150]}{'...' if len(insight.description) > 150 else ''}"

    @staticmethod
    def _format_mentoring_insight(
        category: str, technical: str, experience: str, philosophy: str
    ) -> str:
        """Format mentor-level insight."""
        category_name = category.replace("_", " ").title()

        # Prioritize technical knowledge, then experience lessons
        if technical and len(technical.strip()) > 20:
            return f"[{category_name} Technical Guidance] {technical[:180]}{'...' if len(technical) > 180 else ''}"
        elif experience and len(experience.strip()) > 20:
            return f"[{category_name} Experience Sharing] {experience[:180]}{'...' if len(experience) > 180 else ''}"
        elif philosophy and len(philosophy.strip()) > 20:
            return f"[{category_name} Design Thinking] {philosophy[:180]}{'...' if len(philosophy) > 180 else ''}"

        return None
