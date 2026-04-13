from typing import Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.prompts.templates import FIXER_PROMPT
from src.graph.state import AgentState


class FixProposal(BaseModel):
    proposed_fix: str = Field(
        description="Concrete remediation step that matches the diagnosed root cause.",
    )
    fix_type: Literal["code", "config", "schema"] = Field(
        description="Primary category of the proposed change.",
    )
    fix_reasoning: str = Field(
        description="Why this fix addresses the diagnosed failure mode.",
    )
    estimated_impact: str = Field(
        description="What this change touches or risks in the pipeline.",
    )


def _fallback_fix(state: AgentState) -> FixProposal:
    root_cause = (state.get("root_cause") or "").lower()

    # Offline mode still needs to respect the diagnosis. Hardcoding one fix for every failure was the original bug.
    if "rate limit" in root_cause or "429" in root_cause:
        return FixProposal(
            proposed_fix="Add exponential backoff retry logic with jitter and cap retries at 5 attempts.",
            fix_type="code",
            fix_reasoning="429s are usually transient. Backoff reduces pressure on the upstream API instead of hammering it harder.",
            estimated_impact="Touches the API client retry path and request timing behavior.",
        )

    if "schema" in root_cause:
        return FixProposal(
            proposed_fix="Update the source-to-destination field mapping and add a schema compatibility check before load.",
            fix_type="schema",
            fix_reasoning="The pipeline is likely writing with stale assumptions about source fields.",
            estimated_impact="Touches mapping config and pre-load validation for downstream tables.",
        )

    if "timeout" in root_cause:
        return FixProposal(
            proposed_fix="Increase upstream request timeout to a sane ceiling and add bounded retries around the slow dependency.",
            fix_type="config",
            fix_reasoning="Timeouts usually need a mix of tolerance and retry instead of immediate hard failure.",
            estimated_impact="Touches service timeout config and failure handling around the dependency.",
        )

    return FixProposal(
        proposed_fix="Do not auto-remediate. Capture more logs and send this incident for human review.",
        fix_type="config",
        fix_reasoning="The diagnosis is too weak to safely mutate production behavior.",
        estimated_impact="No system change; only incident handling flow is affected.",
    )


def _invoke_structured_fix(agent: BaseAgent, prompt: str, state: AgentState) -> FixProposal:
    state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

    if agent.llm is None:
        return _fallback_fix(state)

    structured_llm = agent.llm.with_structured_output(FixProposal)
    return structured_llm.invoke(prompt)


def fixer_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Fixer")
    agent.log_action("Proposing fix", state)

    if state.get("retry_counts", {}).get("Fixer", 0) >= 3:
        agent.log_action("Max retries exceeded, escalating", state)
        state["proposed_fix"] = None
        state["final_status"] = "escalated"
        return state

    prompt = FIXER_PROMPT.format(
        root_cause=state.get("root_cause", "unknown"),
        pipeline_config=state.get("pipeline_config", {}),
    )

    try:
        result = _invoke_structured_fix(agent, prompt, state)
    except Exception as error:
        agent.log_action(f"Structured fix generation failed: {error}", state)
        result = _fallback_fix(state)

    state["proposed_fix"] = result.proposed_fix
    state["fix_type"] = result.fix_type
    state["fix_reasoning"] = result.fix_reasoning
    state["estimated_impact"] = result.estimated_impact

    agent.log_action(f"Fix proposed: {result.fix_type}", state)

    state["current_agent"] = "fixer"
    agent.increment_retry(state)

    return state
