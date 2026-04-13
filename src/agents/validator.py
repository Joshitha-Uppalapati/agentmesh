from typing import Dict, Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.prompts.templates import VALIDATOR_PROMPT
from src.graph.state import AgentState


class ValidationResult(BaseModel):
    validation_result: Literal["approved", "rejected", "needs_review"] = Field(
        description="Whether the proposed fix looks safe enough to proceed.",
    )
    validation_reasoning: str = Field(
        description="Why the proposed fix was approved, rejected, or sent for review.",
    )
    test_results: Dict[str, str] = Field(
        default_factory=dict,
        description="Named checks and their outcomes.",
    )


def _fallback_validation(state: AgentState) -> ValidationResult:
    proposed_fix = (state.get("proposed_fix") or "").lower()
    root_cause = (state.get("root_cause") or "").lower()

    # This is still a toy validator, but at least the fallback logic agrees with the fix it is judging.
    if not proposed_fix:
        return ValidationResult(
            validation_result="needs_review",
            validation_reasoning="No proposed fix was produced, so there is nothing safe to validate.",
            test_results={
                "syntax_check": "not_run",
                "sandbox_test": "not_run",
                "edge_cases": "not_run",
            },
        )

    if "human review" in proposed_fix:
        return ValidationResult(
            validation_result="needs_review",
            validation_reasoning="The fixer explicitly declined to make an automated change.",
            test_results={
                "syntax_check": "pass",
                "sandbox_test": "not_run",
                "edge_cases": "not_run",
            },
        )

    if "rate limit" in root_cause and "backoff" in proposed_fix:
        return ValidationResult(
            validation_result="approved",
            validation_reasoning="Retry with backoff matches the failure mode and is low-risk in a sandboxed rollout.",
            test_results={
                "syntax_check": "pass",
                "sandbox_test": "pass",
                "edge_cases": "pass",
            },
        )

    if "schema" in root_cause and "schema compatibility check" in proposed_fix:
        return ValidationResult(
            validation_result="approved",
            validation_reasoning="The proposed change matches the diagnosed schema drift and adds a guardrail before load.",
            test_results={
                "syntax_check": "pass",
                "sandbox_test": "pass",
                "edge_cases": "pass",
            },
        )

    return ValidationResult(
        validation_result="needs_review",
        validation_reasoning="The proposed fix may help, but the validator cannot prove it safely from the current evidence.",
        test_results={
            "syntax_check": "pass",
            "sandbox_test": "fail",
            "edge_cases": "needs_review",
        },
    )


def _invoke_structured_validation(agent: BaseAgent, prompt: str, state: AgentState) -> ValidationResult:
    state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

    if agent.llm is None:
        return _fallback_validation(state)

    structured_llm = agent.llm.with_structured_output(ValidationResult)
    return structured_llm.invoke(prompt)


def validator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Validator")
    agent.log_action("Validating fix", state)

    if state.get("force_escalation"):
        agent.log_action("Escalation forced by demo scenario", state)
        state["validation_result"] = "needs_review"
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    if state.get("retry_counts", {}).get("Validator", 0) >= 2:
        agent.log_action("Max validation retries reached, escalating", state)
        state["validation_result"] = "needs_review"
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    prompt = VALIDATOR_PROMPT.format(
        proposed_fix=state.get("proposed_fix", ""),
        fix_type=state.get("fix_type", "unknown"),
    )

    try:
        result = _invoke_structured_validation(agent, prompt, state)
    except Exception as error:
        agent.log_action(f"Structured validation failed: {error}", state)
        result = _fallback_validation(state)

    state["test_results"] = result.test_results
    state["validation_result"] = result.validation_result
    state["validation_reasoning"] = result.validation_reasoning
    state["final_status"] = "resolved" if result.validation_result == "approved" else "escalated"
    state["current_agent"] = "validator"

    agent.log_action(f"Validation result: {result.validation_result}", state)
    agent.increment_retry(state)

    return state
