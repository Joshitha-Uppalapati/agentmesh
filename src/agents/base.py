import logging
import os
from datetime import UTC, datetime
from typing import Any, Callable, Dict, Tuple, TypeVar

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# Chroma telemetry is just noise in local runs and makes the repo look sloppier than it is.
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

T = TypeVar("T")


class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.llm: BaseChatModel | None = self._init_llm()

    def _init_llm(self) -> BaseChatModel | None:
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

        # Agents own deterministic fallbacks now, so None is enough here.
        return None

    def extract_token_usage(self, response: Any) -> Tuple[int, int]:
        input_tokens = 0
        output_tokens = 0

        metadata = getattr(response, "response_metadata", {}) or {}

        usage = (
            metadata.get("usage")
            or metadata.get("token_usage")
            or {}
        )

        input_tokens = (
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("input_token_count")
            or 0
        )

        output_tokens = (
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("output_token_count")
            or 0
        )

        # LangChain wrappers are inconsistent. Fall back to usage_metadata if either side is missing.
        if input_tokens == 0 or output_tokens == 0:
            usage_meta = getattr(response, "usage_metadata", {}) or {}

            input_tokens = input_tokens or (
                usage_meta.get("input_tokens")
                or usage_meta.get("prompt_tokens")
                or usage_meta.get("input_token_count")
                or 0
            )

            output_tokens = output_tokens or (
                usage_meta.get("output_tokens")
                or usage_meta.get("completion_tokens")
                or usage_meta.get("output_token_count")
                or 0
            )

        return int(input_tokens), int(output_tokens)

    def add_cost_to_state(self, response: Any, state: Dict[str, Any]) -> None:
        if self.llm is None:
            return

        input_tokens, output_tokens = self.extract_token_usage(response)

        if input_tokens == 0 and output_tokens == 0:
            logger.warning(
                "run_id=%s agent=%s missing_token_usage_metadata",
                state.get("run_id"),
                self.name,
            )
            return

        model_name = getattr(self.llm, "model", "").lower()
        cost = 0.0

        # rough pricing as of early 2025. The order matters because these are substring checks.
        # TODO(joshitha): move pricing into config before this spreads any further.
        if "claude" in model_name:
            cost = (input_tokens / 1_000_000) * 3.00 + (output_tokens / 1_000_000) * 15.00
        elif "gpt-4o-mini" in model_name:
            cost = (input_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60
        elif "gpt-4o" in model_name:
            cost = (input_tokens / 1_000_000) * 2.50 + (output_tokens / 1_000_000) * 10.00
        elif "gpt-4" in model_name:
            cost = (input_tokens / 1_000_000) * 10.00 + (output_tokens / 1_000_000) * 30.00

        state["total_cost_usd"] = round(
            state.get("total_cost_usd", 0.0) + cost,
            6,
        )

    def invoke_structured(
        self,
        model_cls: type[T],
        prompt: str,
        state: Dict[str, Any],
        fallback_fn: Callable[[], T],
    ) -> T:
        state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

        if self.llm is None:
            self.log_action("No LLM configured; using fallback logic.", state)
            return fallback_fn()

        try:
            structured_llm = self.llm.with_structured_output(
                model_cls,
                include_raw=True,
            )

            raw_output = structured_llm.invoke(
                prompt,
                config={"timeout": 30},
            )

            raw_message = raw_output.get("raw")
            parsed = raw_output.get("parsed")
            
            usage_source = raw_message if raw_message is not None else raw_output
            self.add_cost_to_state(usage_source, state)
            
            if parsed is None:
                logger.warning(
                    "run_id=%s agent=%s missing_parsed_structured_output_using_fallback",
                    state.get("run_id"),
                    self.name,
                )
                return fallback_fn()
            return parsed

        except Exception as error:
            self.log_action(
                f"Structured invocation failed; using fallback logic. reason={error}",
                state,
            )
            return fallback_fn()

    def call_llm(self, prompt: str, state: Dict[str, Any]) -> Any:
        """
        Central raw LLM invocation.

        Structured output should go through invoke_structured(). This wrapper stays
        around for any direct/raw calls that still need shared accounting.
        """

        state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

        if self.llm is None:
            raise RuntimeError("No LLM configured for direct invocation.")

        try:
            response = self.llm.invoke(
                prompt,
                config={"timeout": 30},
            )
        except Exception as error:
            logger.warning(
                "run_id=%s agent=%s llm_call_failed error=%s",
                state.get("run_id"),
                self.name,
                str(error),
            )
            raise

        self.add_cost_to_state(response, state)
        return response

    def increment_retry(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if "retry_counts" not in state:
            # LangGraph merges node outputs, but nested dict mutation still bites
            # when the bucket was never initialized.
            state["retry_counts"] = {}

        state["retry_counts"][self.name] = state["retry_counts"].get(self.name, 0) + 1
        return state

    def log_action(self, action: str, state: Dict[str, Any]) -> None:
        timestamp = datetime.now(UTC).isoformat()

        logger.info(
            "run_id=%s agent=%s pipeline=%s ts=%s action=%s",
            state.get("run_id"),
            self.name,
            state.get("pipeline_id"),
            timestamp,
            action,
        )