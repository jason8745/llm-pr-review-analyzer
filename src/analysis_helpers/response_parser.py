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
            # Clean up the response
            response = response.strip()

            # Try to find JSON block markers
            json_markers = ["```json", "```"]
            for marker in json_markers:
                if marker in response:
                    start_idx = response.find(marker) + len(marker)
                    if marker == "```json":
                        end_idx = response.find("```", start_idx)
                    else:
                        end_idx = response.find("```", start_idx)

                    if end_idx > start_idx:
                        json_str = response[start_idx:end_idx].strip()
                        return json.loads(json_str)

            # Extract JSON from response if it contains other text
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)

            # Try parsing the entire response as JSON
            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}...")

            # Return a fallback structured response
            return {
                "description": response[:500] if response else "No response received",
                "severity": "low",
                "learning_opportunities": ["Review the response manually"],
                "actionable_guidance": ["Check the LLM output format"],
            }
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return None

    def get_format_instructions(self) -> str:
        """Return format instructions for the LLM."""
        return """Please respond with valid JSON format only. 
        Ensure all strings are properly escaped and the JSON is well-formed."""
