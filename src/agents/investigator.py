from typing import List

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


def _build_investigation_fallback(symptoms: str, similar_failures: List[str]) -> InvestigationResult:
    # Keep fallback deterministic — debugging random behavior here is painful.
    sample_logs = SAMPLE_LOGS.splitlines()
    joined = f"{symptoms} {' '.join(similar_failures)}".lower()

    if "429" in joined or "rate limit" in joined:
        return InvestigationResult(
            root_cause="Source API rate limit exceeded",
            confidence_score=0.85,
            relevant_logs=[line for line in sample_logs if "429" in line or "Retry" in line][:3],
        )

    if "schema" in joined or "missing data" in joined:
        return InvestigationResult(
            root_cause="Schema mismatch between source and destination",
            confidence_score=0.70,
            relevant_logs=sample_logs[:2],
        )

    if "timeout" in joined:
        return InvestigationResult(
            root_cause="Upstream service timeout",
            confidence_score=0.65,
            relevant_logs=sample_logs[:2],
        )

    return InvestigationResult(
        root_cause="Unable to diagnose automatically",
        confidence_score=0.25,
        relevant_logs=sample_logs[:2],
    )


def investigator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Investigator")
    agent.log_action("Starting investigation", state)

    symptoms = ", ".join(state.get("failure_symptoms", []))

    vector_store = VectorStore()
    similar_failures: List[str] = vector_store.query(symptoms, k=2)

    prompt = INVESTIGATOR_PROMPT.format(
        failure_symptoms=symptoms,
        logs=SAMPLE_LOGS,
        similar_failures="\n".join(similar_failures) if similar_failures else "None",
    )

    result = agent.invoke_structured(
        InvestigationResult,
        prompt,
        state,
        fallback_fn=lambda: _build_investigation_fallback(symptoms, similar_failures),
    )

    confidence = min(result.confidence_score, 0.85)

    state["investigation_complete"] = True
    state["root_cause"] = result.root_cause
    state["confidence_score"] = confidence
    state["relevant_logs"] = result.relevant_logs
    state["similar_past_failures"] = [{"symptoms": item} for item in similar_failures]
    state["current_agent"] = "investigator"

    agent.log_action(
        f"Diagnosis: {result.root_cause} (confidence={confidence:.2f})",
        state,
    )

    if confidence < 0.6:
        state["proposed_fix"] = None
        state["fix_type"] = None
        state["fix_reasoning"] = "Diagnostic confidence too low for automated remediation"

        agent.log_action(
            "Low diagnostic confidence; escalating instead of auto-fixing",
            state,
        )

    return state