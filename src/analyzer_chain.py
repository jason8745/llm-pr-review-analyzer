"""LLM analysis chain for PR review comment analysis using LCEL."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.schema import BaseOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import AzureChatOpenAI

from analysis_helpers import (
    AnalysisResultBuilder,
    InsightExtractor,
    ProfileBuilder,
    PromptTemplates,
    ResponseParser,
)
from config.config import Config, get_config
from models.analysis_result import (
    AnalysisResult,
    ReviewCategory,
    ReviewerProfile,
    ReviewInsight,
    Severity,
)
from utils import ChainExecutor, LLMAnalysisError, ReviewerCommentProcessor, get_logger

logger = get_logger(__name__)


def get_llm_client(config: Optional[Config] = None) -> AzureChatOpenAI:
    """Return AzureChatOpenAI client for PR review analysis."""
    if config is None:
        config = get_config()

    logger.info(
        f"Creating Azure OpenAI client with deployment: {config.azure_openai.deployment}"
    )
    logger.info(f"Endpoint: {config.azure_openai.endpoint}")
    logger.info(f"API version: {config.azure_openai.api_version}")
    logger.info(
        f"Temperature: {config.llm.temperature}, Max tokens: {config.llm.max_tokens}"
    )

    try:
        client = AzureChatOpenAI(
            azure_deployment=config.azure_openai.deployment,
            azure_endpoint=config.azure_openai.endpoint,
            api_version=config.azure_openai.api_version,
            api_key=config.azure_openai.api_key.get_secret_value(),
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
        logger.info("Azure OpenAI client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Azure OpenAI client: {e}")
        raise LLMAnalysisError(f"Azure OpenAI client initialization failed: {e}")


class ReviewAnalyzer:
    """LLM-powered PR review comment analyzer using LCEL chains."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize review analyzer.

        Args:
            config: Application configuration
        """
        self.config = config or get_config()
        self.llm = get_llm_client(self.config)
        self.parser = ResponseParser()

        # Initialize utility classes
        self.chain_executor = ChainExecutor(self.config.llm.retry)
        self.comment_processor = ReviewerCommentProcessor()
        self.result_builder = AnalysisResultBuilder()

        # Initialize LCEL chains
        self._setup_chains()

    def _setup_chains(self):
        """Setup LCEL chains for different analysis tasks."""
        # Reviewer insight analysis chain
        self.insight_chain = (
            PromptTemplates.create_reviewer_insight_prompt() | self.llm | self.parser
        )

        # Overall pattern analysis chain
        self.overall_chain = (
            PromptTemplates.create_overall_analysis_prompt() | self.llm | self.parser
        )

    def analyze_comments(self, prepared_data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze prepared comment data using LLM chains.

        Args:
            prepared_data: Output from CommentPreparer

        Returns:
            Structured analysis results
        """
        logger.info("Starting LLM analysis of prepared comments")

        try:
            # Extract basic info
            stats = prepared_data["statistics"]
            grouped_data = prepared_data["grouped_data"]

            # Separate PR creator from reviewers
            pr_creator = stats["pr_info"]["author"]
            reviewer_comments = self.comment_processor.separate_reviewer_comments(
                grouped_data["by_reviewer"], pr_creator
            )

            # Build analysis pipeline using LCEL
            analysis_pipeline = (
                RunnablePassthrough.assign(
                    insights=lambda x: self._analyze_reviewer_insights(
                        x["prepared_data"], x["reviewer_comments"]
                    ),
                    reviewer_profiles=lambda x: ProfileBuilder.build_reviewer_profiles(
                        x["reviewer_comments"]
                    ),
                )
                | RunnablePassthrough.assign(
                    key_knowledge_insights=lambda x: InsightExtractor.extract_knowledge_insights(
                        x["insights"]
                    ),
                    learning_opportunities=lambda x: InsightExtractor.extract_learning_opportunities(
                        x["insights"]
                    ),
                    mentoring_insights=lambda x: InsightExtractor.extract_mentoring_insights(
                        x["insights"]
                    ),
                    valuable_insights=lambda x: InsightExtractor.extract_valuable_insights(
                        x["insights"], x["prepared_data"]
                    ),
                )
                | RunnableLambda(
                    lambda x: self.result_builder.build_analysis_result(x, stats)
                )
            )

            # Execute the pipeline
            result = analysis_pipeline.invoke(
                {
                    "prepared_data": prepared_data,
                    "reviewer_comments": reviewer_comments,
                    "pr_creator": pr_creator,
                }
            )

            logger.info(
                f"Analysis completed: {len(result.insights)} insights from {len(reviewer_comments)} reviewers"
            )
            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise LLMAnalysisError(f"Failed to analyze comments: {e}")

    def _analyze_reviewer_insights(
        self, pipeline_data: Dict[str, Any], reviewer_comments: Dict[str, List]
    ) -> List[ReviewInsight]:
        """Analyze reviewer insights focusing on their knowledge and concerns."""
        insights = []

        # Get prepared_data from pipeline_data
        prepared_data = pipeline_data.get("prepared_data", pipeline_data)

        # Analyze by category (only reviewer comments)
        reviewer_categories = self.comment_processor.categorize_reviewer_comments(
            prepared_data["grouped_data"]["by_category"],
            prepared_data["statistics"]["pr_info"]["author"],
        )

        # Process each category with LCEL chain
        for category, comments in reviewer_categories.items():
            if len(comments) > 0:
                insight = self._analyze_category_with_chain(
                    category, comments, prepared_data["statistics"]
                )
                if insight:
                    insights.append(insight)

        # Analyze overall reviewer patterns
        overall_insight = self._analyze_overall_patterns(
            prepared_data, reviewer_comments
        )
        if overall_insight:
            insights.append(overall_insight)

        return insights

    def _analyze_category_with_chain(
        self, category: ReviewCategory, comments: List, pr_stats: Dict
    ) -> Optional[ReviewInsight]:
        """Analyze reviewer insights within a specific category using LCEL chain."""
        if len(comments) < 1:
            return None

        try:
            # Prepare input for the chain
            chain_input = {
                "repository": pr_stats["pr_info"]["repository"],
                "pr_number": pr_stats["pr_info"]["number"],
                "pr_title": pr_stats["pr_info"]["title"],
                "pr_creator": pr_stats["pr_info"]["author"],
                "category": category.value,
                "comment_samples": PromptTemplates.format_comment_samples(comments),
            }

            # Execute chain with retry logic
            analysis_data = self.chain_executor.execute_with_retry(
                self.insight_chain, chain_input
            )

            if analysis_data:
                # Validate that analysis_data is a dict
                if not isinstance(analysis_data, dict):
                    logger.warning(
                        f"Expected dict from LLM but got {type(analysis_data)}: {analysis_data}"
                    )
                    return None

                # Use the new from_llm_response method if data is comprehensive
                if isinstance(analysis_data, dict) and (
                    "reviewer_insights" in analysis_data
                    or "learning_opportunities" in analysis_data
                    or "actionable_guidance" in analysis_data
                ):
                    analysis_data["category"] = category.value
                    analysis_data["frequency"] = len(comments)
                    return ReviewInsight.from_llm_response(analysis_data)
                else:
                    # Fallback to basic ReviewInsight for simple responses
                    return ReviewInsight(
                        category=category,
                        description=analysis_data.get("description", ""),
                        frequency=len(comments),
                        severity=Severity(
                            analysis_data.get("severity", "medium").lower()
                        ),
                        examples=[
                            c.content[:100] + "..."
                            if len(c.content) > 100
                            else c.content
                            for c in comments[:2]
                        ],
                        reviewers_mentioned=[c.author for c in comments],
                    )
        except Exception as e:
            logger.warning(
                f"Failed to analyze reviewer insights for {category.value}: {e}"
            )

        return None

    def _analyze_overall_patterns(
        self, prepared_data: Dict[str, Any], reviewer_comments: Dict[str, List]
    ) -> Optional[ReviewInsight]:
        """Analyze overall reviewer patterns using LCEL chain."""
        try:
            stats = prepared_data["statistics"]

            chain_input = {
                "repository": stats["pr_info"]["repository"],
                "pr_number": stats["pr_info"]["number"],
                "pr_title": stats["pr_info"]["title"],
                "pr_creator": stats["pr_info"]["author"],
                "total_comments": stats["total_comments"],
                "reviewer_count": len(reviewer_comments),
                "reviewer_summary": PromptTemplates.format_reviewer_summary(
                    reviewer_comments
                ),
                "categories": ", ".join(
                    [
                        cat.value
                        for cat in prepared_data["grouped_data"]["by_category"].keys()
                    ]
                ),
            }

            analysis_data = self.chain_executor.execute_with_retry(
                self.overall_chain, chain_input
            )

            if analysis_data:
                # Use the new from_llm_response method if data is comprehensive
                if isinstance(analysis_data, dict) and (
                    "reviewer_insights" in analysis_data
                    or "learning_opportunities" in analysis_data
                    or "actionable_guidance" in analysis_data
                ):
                    analysis_data["category"] = "other"
                    analysis_data["frequency"] = stats["total_comments"]
                    return ReviewInsight.from_llm_response(analysis_data)
                else:
                    # Fallback to basic ReviewInsight for simple responses
                    return ReviewInsight(
                        category=ReviewCategory.OTHER,
                        description=analysis_data.get("description", ""),
                        frequency=sum(
                            len(comments) for comments in reviewer_comments.values()
                        ),
                        severity=Severity(analysis_data.get("severity", "low").lower()),
                        examples=[],
                        reviewers_mentioned=list(reviewer_comments.keys()),
                    )
        except Exception as e:
            logger.warning(f"Failed to analyze overall reviewer patterns: {e}")

        return None
