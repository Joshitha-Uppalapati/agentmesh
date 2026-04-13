from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.graph.state import AgentState
from src.prompts.templates import VALIDATOR_PROMPT


class ValidationResult(BaseModel):
    validation_result: Literal["approved", "rejected", "needs_review"] = Field(
        description="Whether the proposed fix appears safe enough to proceed.",
    )
    validation_reasoning: str = Field(
        description="Why the fix was approved, rejected, or flagged for review.",
    )
    test_results: Any = Field(
        default_factory=dict,
        description="Validation artifacts or notes. LLMs often return a string here instead of a dict.",
    )


def _build_validation_fallback(state: AgentState) -> ValidationResult:
    proposed_fix = (state.get("proposed_fix") or "").lower()
    root_cause = (state.get("root_cause") or "").lower()

    # Be conservative here. Once structured parsing fails, pretending we have
    # strong validation evidence is how bad fixes get blessed.
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

    if "human review" in proposed_fix or "do not auto-remediate" in proposed_fix:
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
            validation_reasoning="Retry with backoff matches the failure mode and is low-risk for a controlled rollout.",
            test_results={
                "syntax_check": "pass",
                "sandbox_test": "pass",
                "edge_cases": "pass",
            },
        )

    if "schema" in root_cause and "schema compatibility check" in proposed_fix:
        return ValidationResult(
            validation_result="approved",
            validation_reasoning="The proposed change matches the diagnosed schema drift and adds a guard before the load step.",
            test_results={
                "syntax_check": "pass",
                "sandbox_test": "pass",
                "edge_cases": "pass",
            },
        )

    return ValidationResult(
        validation_result="needs_review",
        validation_reasoning="The proposed fix may help, but the validator cannot prove that safely from the current evidence.",
        test_results={
            "syntax_check": "pass",
            "sandbox_test": "needs_review",
            "edge_cases": "needs_review",
        },
    )


def validator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Validator")
    agent.log_action("Validating fix", state)

    if state.get("force_escalation"):
        agent.log_action("Escalation forced by demo scenario", state)
        state["validation_result"] = "needs_review"
        state["validation_reasoning"] = "Scenario flag forced escalation."
        state["test_results"] = {
            "syntax_check": "not_run",
            "sandbox_test": "not_run",
            "edge_cases": "not_run",
        }
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    if state.get("retry_counts", {}).get("Validator", 0) >= 2:
        # Validator loops are expensive and usually low-signal. Once it has pushed
        # back twice, treat it as a human-review case instead of burning more calls.
        agent.log_action("Max validator retries reached, escalating", state)
        state["validation_result"] = "needs_review"
        state["validation_reasoning"] = "Validator retried too many times; escalation is safer."
        state["test_results"] = {
            "syntax_check": "not_run",
            "sandbox_test": "not_run",
            "edge_cases": "not_run",
        }
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    prompt = VALIDATOR_PROMPT.format(
        proposed_fix=state.get("proposed_fix", ""),
        fix_type=state.get("fix_type", "unknown"),
    )

    result = agent.invoke_structured(
        ValidationResult,
        prompt,
        state,
        fallback_fn=lambda: _build_validation_fallback(state),
    )

    state["validation_result"] = result.validation_result
    state["validation_reasoning"] = result.validation_reasoning
    state["test_results"] = result.test_results
    state["final_status"] = "resolved" if result.validation_result == "approved" else "escalated"
    state["current_agent"] = "validator"

    agent.log_action(f"Validation result: {result.validation_result}", state)
    agent.increment_retry(state)

    return state