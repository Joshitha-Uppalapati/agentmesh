from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.graph.state import AgentState
from src.prompts.templates import INVESTIGATOR_PROMPT
from src.tools.log_analyzer import SAMPLE_LOGS
from src.tools.vector_store import VectorStore


class InvestigationResult(BaseModel):
    root_cause: str = Field(
        description="Clear diagnosis of what most likely failed in the pipeline.",
    )
    # confidence is a model hallucination risk, but still useful for routing.
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the model is in the diagnosis.",
    )
    relevant_logs: List[str] = Field(
        default_factory=list,
        description="Most relevant log lines supporting the diagnosis.",
    )


def _fallback_investigation(similar_failures: List[Dict[str, Any]]) -> InvestigationResult:
    # Offline mode should stay deterministic. Fancy fake parsers bought us nothing except test flakiness.
    sample_logs = SAMPLE_LOGS.splitlines()
    root_cause = "Unable to diagnose automatically"
    confidence_score = 0.25
    relevant_logs = sample_logs[:2]

    if "429" in SAMPLE_LOGS or "rate limit" in SAMPLE_LOGS.lower():
        root_cause = "Source API rate limit exceeded"
        confidence_score = 0.85
        relevant_logs = [line for line in sample_logs if "429" in line or "Retry" in line][:3]
    elif similar_failures:
        root_cause = similar_failures[0].get("root_cause") or root_cause
        confidence_score = 0.65

    return InvestigationResult(
        root_cause=root_cause,
        confidence_score=confidence_score,
        relevant_logs=relevant_logs,
    )


def _invoke_structured_investigator(
    agent: BaseAgent,
    prompt: str,
    state: AgentState,
    similar_failures: List[Dict[str, Any]],
) -> InvestigationResult:
    state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1

    if agent.llm is None:
        return _fallback_investigation(similar_failures)

    structured_llm = agent.llm.with_structured_output(InvestigationResult)
    result = structured_llm.invoke(prompt)

    # The model occasionally spikes high confidence on vague evidence.
    # Keep the cap close to the agent, not buried in the router.
    result.confidence_score = min(result.confidence_score, 0.85)
    return result


def investigator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Investigator")
    agent.log_action("Starting investigation", state)

    symptoms = ", ".join(state.get("failure_symptoms", []))

    vector_store = VectorStore()
    similar_failures = vector_store.search_similar(symptoms, n_results=2)

    prompt = INVESTIGATOR_PROMPT.format(
        failure_symptoms=symptoms,
        logs=SAMPLE_LOGS,
        similar_failures=similar_failures,
    )

    try:
        result = _invoke_structured_investigator(
            agent,
            prompt,
            state,
            similar_failures,
        )
    except Exception as error:
        agent.log_action(f"Structured investigation failed: {error}", state)
        result = InvestigationResult(
            root_cause="Unable to diagnose automatically",
            confidence_score=0.0,
            relevant_logs=[],
        )

    result.confidence_score = min(result.confidence_score, 0.85)

    state["investigation_complete"] = True
    state["root_cause"] = result.root_cause
    state["confidence_score"] = result.confidence_score
    state["relevant_logs"] = result.relevant_logs
    state["similar_past_failures"] = similar_failures
    state["current_agent"] = "investigator"

    agent.log_action(
        f"Diagnosis: {result.root_cause} (confidence={result.confidence_score:.2f})",
        state,
    )

    if result.confidence_score < 0.6:
        state["proposed_fix"] = None
        state["fix_type"] = None
        state["fix_reasoning"] = "Diagnostic confidence too low for automated remediation"

        agent.log_action(
            "Low diagnostic confidence; escalating instead of auto-fixing",
            state,
        )

    return state
