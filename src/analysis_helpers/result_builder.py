"""Analysis result builder for creating final AnalysisResult objects."""

from datetime import datetime
from typing import Any, Dict

from models.analysis_result import AnalysisResult


class AnalysisResultBuilder:
    """Builder class for constructing AnalysisResult objects."""

    def __init__(self):
        """Initialize the builder."""
        pass

    def build_analysis_result(self, analysis_data: Dict, stats: Dict) -> AnalysisResult:
        """Build final AnalysisResult from pipeline data with streamlined focus."""
        return AnalysisResult(
            repository=stats["pr_info"]["repository"],
            pr_number=stats["pr_info"]["number"],
            analysis_timestamp=datetime.now().isoformat(),
            insights=analysis_data["insights"],
            reviewer_profiles=analysis_data["reviewer_profiles"],
            # Core output fields used in the 5-section format
            key_knowledge_insights=analysis_data.get("key_knowledge_insights", []),
            learning_opportunities=analysis_data.get("learning_opportunities", {}),
            mentoring_insights=analysis_data.get("mentoring_insights", []),
            valuable_insights=analysis_data.get("valuable_insights", {}),
        )
