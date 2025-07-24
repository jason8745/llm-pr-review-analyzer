"""Response parser for LLM outputs."""

import json
from typing import Any, Dict, Optional

from langchain.schema.output_parser import BaseOutputParser

from utils import get_logger

logger = get_logger(__name__)


class ResponseParser(BaseOutputParser):
    """Parse LLM JSON responses into structured data."""

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response text into structured data."""
        return self.parse_llm_response(text)

    @staticmethod
    def parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response."""
        try:
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response length: {len(response) if response else 0}")
            logger.debug(f"Raw LLM response type: {type(response)}")

            # Handle None or empty responses
            if not response or not response.strip():
                logger.warning("Received empty or None response from LLM")
                return ResponseParser._create_fallback_response(
                    "Empty response from LLM"
                )

            # Clean up the response
            response = response.strip()
            logger.debug(
                f"Cleaned response preview: {response[:200]}{'...' if len(response) > 200 else ''}"
            )

            # Try to find JSON block markers with improved logic
            if "```json" in response:
                # Extract content between ```json and ```
                start_marker = "```json"
                end_marker = "```"
                start_idx = response.find(start_marker) + len(start_marker)
                end_idx = response.find(end_marker, start_idx)

                if end_idx > start_idx:
                    json_str = response[start_idx:end_idx].strip()
                    logger.debug(
                        f"Extracted JSON from ```json block: {json_str[:100]}..."
                    )
                    return json.loads(json_str)
            elif "```" in response:
                # Handle generic code blocks that might contain JSON
                lines = response.split("\n")
                in_code_block = False
                json_lines = []

                for line in lines:
                    if line.strip() == "```" and not in_code_block:
                        in_code_block = True
                        continue
                    elif line.strip() == "```" and in_code_block:
                        break
                    elif in_code_block:
                        json_lines.append(line)

                if json_lines:
                    json_str = "\n".join(json_lines).strip()
                    logger.debug(
                        f"Extracted JSON from generic code block: {json_str[:100]}..."
                    )
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.debug(
                            "Failed to parse extracted code block as JSON, continuing..."
                        )
                        pass

            # Extract JSON from response if it contains other text
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                logger.debug(f"Extracted JSON from braces: {json_str[:100]}...")
                return json.loads(json_str)

            # Try parsing the entire response as JSON
            logger.debug("Attempting to parse entire response as JSON")
            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}...")

            return ResponseParser._create_fallback_response(
                response[:500] if response else "No response received"
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return ResponseParser._create_fallback_response(f"Parsing error: {str(e)}")

    @staticmethod
    def _create_fallback_response(error_message: str) -> Dict[str, Any]:
        """Create a fallback response when parsing fails."""
        return {
            "description": error_message,
            "severity": "low",
            "knowledge_category": "other",
            "reviewer_insights": {
                "technical_knowledge": "Response parsing failed",
                "experience_lessons": "Review LLM output format",
                "design_philosophy": "Ensure proper JSON formatting",
            },
            "actionable_guidance": {
                "immediate_actions": [
                    "Check the LLM output format",
                    "Review response manually",
                ]
            },
            "reviewer_responses": [],
        }

    def get_format_instructions(self) -> str:
        """Return format instructions for the LLM."""
        return """Please respond with valid JSON format only. 
        Ensure all strings are properly escaped and the JSON is well-formed."""
