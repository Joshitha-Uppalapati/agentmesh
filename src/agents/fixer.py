from typing import Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.graph.state import AgentState
from src.prompts.templates import FIXER_PROMPT


class FixProposal(BaseModel):
    proposed_fix: str = Field(
        description="Concrete remediation step that matches the diagnosed failure mode.",
    )
    fix_type: Literal["code", "config", "schema"] = Field(
        description="Primary category of the proposed change.",
    )
    fix_reasoning: str = Field(
        description="Why this fix is a reasonable response to the diagnosed issue.",
    )
    estimated_impact: str = Field(
        description="What parts of the pipeline this change is likely to touch.",
    )


def _build_fix_fallback(state: AgentState) -> FixProposal:
    root_cause = (state.get("root_cause") or "").lower()

    # Fallback has to respect the diagnosis. One generic fix for every failure
    # was the original bug and it made the whole graph look smarter than it was.
    if "rate limit" in root_cause or "429" in root_cause:
        return FixProposal(
            proposed_fix="Add exponential backoff with jitter, cap retries at 5 attempts, and surface rate-limit metrics in the client.",
            fix_type="code",
            fix_reasoning="Rate-limit failures are usually transient. Backoff reduces pressure on the upstream API instead of turning a brief quota issue into a self-inflicted outage.",
            estimated_impact="Touches API client retry behavior and request pacing.",
        )

    if "schema" in root_cause:
        return FixProposal(
            proposed_fix="Update the source-to-destination field mapping and add a schema compatibility check before the load step.",
            fix_type="schema",
            fix_reasoning="Schema drift usually means the pipeline is writing with stale assumptions about incoming fields.",
            estimated_impact="Touches mapping logic and pre-load validation for downstream tables.",
        )

    if "timeout" in root_cause:
        return FixProposal(
            proposed_fix="Increase the upstream timeout ceiling slightly and add bounded retries around the slow dependency.",
            fix_type="config",
            fix_reasoning="Timeout failures usually need a mix of patience and bounded retry, not a blind hard stop on the first slow response.",
            estimated_impact="Touches dependency timeout configuration and failure handling.",
        )

    return FixProposal(
        proposed_fix="Do not auto-remediate. Capture more logs and route this incident for human review.",
        fix_type="config",
        fix_reasoning="The diagnosis is too weak to justify mutating production behavior automatically.",
        estimated_impact="No production change; only the incident-handling path is affected.",
    )


def fixer_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Fixer")
    agent.log_action("Proposing fix", state)

    if state.get("retry_counts", {}).get("Fixer", 0) >= 3:
        # Once the fixer starts looping, you usually learn nothing new from another
        # LLM call except a bigger bill.
        agent.log_action("Max fixer retries reached, escalating", state)
        state["proposed_fix"] = None
        state["fix_type"] = None
        state["fix_reasoning"] = "Fix generation retried too many times; escalation is safer."
        state["estimated_impact"] = "No automated change applied."
        state["final_status"] = "escalated"
        state["current_agent"] = "fixer"
        return state

    prompt = FIXER_PROMPT.format(
        root_cause=state.get("root_cause", "unknown"),
        pipeline_config=state.get("pipeline_config", {}),
    )

    result = agent.invoke_structured(
        FixProposal,
        prompt,
        state,
        fallback_fn=lambda: _build_fix_fallback(state),
    )

    state["proposed_fix"] = result.proposed_fix
    state["fix_type"] = result.fix_type
    state["fix_reasoning"] = result.fix_reasoning
    state["estimated_impact"] = result.estimated_impact
    state["current_agent"] = "fixer"

    agent.log_action(f"Fix proposed: {result.fix_type}", state)
    agent.increment_retry(state)

    return state