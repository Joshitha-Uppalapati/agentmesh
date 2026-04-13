import logging
import os
from datetime import datetime
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.llm: BaseChatModel = self._init_llm()

    def _init_llm(self) -> BaseChatModel:
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

        # No more silent demo fallback.
        # If someone runs this without a key, it should fail loudly.
        raise RuntimeError("No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")

    def call_llm(self, prompt: str, state: Dict[str, Any]) -> Any:
        """
        Central LLM invocation.

        Structured output happens at the call site (agent level).
        This just handles accounting + failure visibility.
        """

        state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

        try:
            # TODO(joshitha): add timeout + retry (tenacity)
            # Right now one hung request blocks the whole graph.
            response = self.llm.invoke(prompt)

        except Exception as e:
            # This used to fall back to fake responses, which made debugging impossible.
            logger.warning("llm invocation failed: %s", e)
            raise

        # Cost tracking (still useful for demo realism)
        usage = getattr(response, "response_metadata", {}).get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        model_name = getattr(self.llm, "model", "").lower()
        cost = 0.0

        # rough pricing as of early 2025 — will drift
        # TODO(joshitha): move to config before this leaks into real usage
        if "claude" in model_name:
            cost = (input_tokens / 1_000_000) * 3.00 + (output_tokens / 1_000_000) * 15.00
        elif "gpt-4" in model_name:
            cost = (input_tokens / 1_000_000) * 10.00 + (output_tokens / 1_000_000) * 30.00

        state["total_cost_usd"] = round(
            state.get("total_cost_usd", 0.0) + cost,
            6,
        )

        return response

    def increment_retry(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if "retry_counts" not in state:
            # LangGraph merges node outputs, but nested dict mutation still bites if missing.
            state["retry_counts"] = {}

        state["retry_counts"][self.name] = state["retry_counts"].get(self.name, 0) + 1
        return state

    def log_action(self, action: str, state: Dict[str, Any]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        pipeline = state.get("pipeline_id", "unknown")

        # print() makes logs useless once you have concurrent runs
        logger.info("%s | %s | %s | %s", timestamp, self.name, pipeline, action)