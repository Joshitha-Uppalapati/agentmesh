from src.agents.base import BaseAgent
from src.prompts.templates import INVESTIGATOR_PROMPT
from src.graph.state import AgentState
from src.tools.log_analyzer import SAMPLE_LOGS
from src.tools.vector_store import VectorStore


"""
Investigator Agent - Real LLM integration
"""


def investigator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Investigator")
    agent.log_action("Starting investigation", state)

    # Build symptom context
    symptoms = ", ".join(state.get("failure_symptoms", []))

    # Retrieve similar past failures
    vector_store = VectorStore()
    similar_failures = vector_store.search_similar(symptoms, n_results=2)

    # Construct prompt
    prompt = INVESTIGATOR_PROMPT.format(
        failure_symptoms=symptoms,
        logs=SAMPLE_LOGS,
        similar_failures=similar_failures,
    )

    try:
        response = agent.call_llm(prompt, state)
    except Exception as e:
        agent.log_action(f"LLM call failed: {e}", state)
        state["investigation_complete"] = True
        state["root_cause"] = "Unable to diagnose automatically"
        state["confidence_score"] = 0.0
        state["relevant_logs"] = []
        state["current_agent"] = "investigator"
        return state

    response_lower = response.lower()

    root_cause = "Unknown failure"
    confidence = 0.4  # default: low confidence

    if "429" in response_lower or "rate limit" in response_lower:
        root_cause = "Source API rate limit exceeded"
        confidence = 0.85
    elif "schema" in response_lower:
        root_cause = "Schema mismatch between source and destination"
        confidence = 0.75
    elif "timeout" in response_lower:
        root_cause = "Upstream service timeout"
        confidence = 0.65

    # Cap confidence intentionally — automated diagnosis should not be absolute
    confidence = min(confidence, 0.85)

    state["investigation_complete"] = True
    state["root_cause"] = root_cause
    state["confidence_score"] = confidence
    state["relevant_logs"] = SAMPLE_LOGS[:2]
    state["current_agent"] = "investigator"

    agent.log_action(
        f"Diagnosis: {root_cause} (confidence={confidence:.2f})",
        state,
    )

    # Confidence-based gating
    if confidence < 0.6:
        state["proposed_fix"] = None
        state["fix_type"] = None
        state["fix_reasoning"] = "Diagnostic confidence too low for automated remediation"

        agent.log_action(
            "Low diagnostic confidence; escalating instead of auto-fixing",
            state,
        )

    return state
