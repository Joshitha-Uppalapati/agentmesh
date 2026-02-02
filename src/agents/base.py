from typing import Dict, Any
from datetime import datetime
import os


class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.llm = self._init_llm()

    def _init_llm(self):
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if anthropic_key:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=anthropic_key,
            )

        if openai_key:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
            )

        return None  # fallback to mock mode

    def call_llm(self, prompt: str, state: Dict[str, Any]) -> str:
        """
        Execute an LLM call and track usage.
        Falls back to mock responses if no API key is present.
        """

        if self.llm is None:
            state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1
            return self._mock_response(prompt, state)

        response = self.llm.invoke(prompt)
        output_text = response.content

        # usage tracking
        state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

        usage = response.response_metadata.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        model_name = getattr(self.llm, "model", "").lower()
        cost = 0.0

        if "claude" in model_name:
            cost = (input_tokens / 1_000_000) * 3.00 + (output_tokens / 1_000_000) * 15.00
        elif "gpt-4" in model_name:
            cost = (input_tokens / 1_000_000) * 10.00 + (output_tokens / 1_000_000) * 30.00

        state["total_cost_usd"] = round(
            state.get("total_cost_usd", 0.0) + cost,
            6,
        )

        return output_text

    def _mock_response(self, prompt: str, state: Dict[str, Any]) -> str:
        if "Monitor" in self.name:
            return """health_status: failed
failure_detected: true
failure_symptoms: ["Missing data in target table orders_daily", "Last successful run was 6 hours ago"]"""

        if "Investigator" in self.name:
            return """root_cause: Source API rate limit exceeded - receiving 429 errors
confidence_score: 0.85
relevant_logs: ["2024-01-15 10:23:45 ERROR: API returned 429", "2024-01-15 10:23:46 WARN: Retry attempt 3 failed"]"""

        if "Fixer" in self.name:
            return """proposed_fix: Add exponential backoff retry logic with max 5 attempts and 60s delay
fix_type: code
fix_reasoning: Rate limit errors need retry logic to handle temporary API unavailability
estimated_impact: Affects API client module, no schema changes"""

        if "Validator" in self.name:
            return """validation_result: approved
validation_reasoning: Retry logic properly implements exponential backoff, tested with simulated rate limits
test_results: {"syntax_check": "pass", "sandbox_test": "pass", "edge_cases": "pass"}"""

        return "Mock response"

    def increment_retry(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if "retry_counts" not in state:
            state["retry_counts"] = {}

        state["retry_counts"][self.name] = state["retry_counts"].get(self.name, 0) + 1
        return state

    def log_action(self, action: str, state: Dict[str, Any]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        pipeline = state.get("pipeline_id", "unknown")
        print(f"[{timestamp}] {self.name} | {pipeline} | {action}")