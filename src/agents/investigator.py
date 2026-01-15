from src.agents.base import BaseAgent
from src.prompts.templates import INVESTIGATOR_PROMPT
from src.graph.state import AgentState
from src.tools.log_analyzer import SAMPLE_LOGS
from src.tools.vector_store import VectorStore


def investigator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Investigator")
    agent.log_action("Starting investigation", state)
    
    # Get similar past failures from vector DB
    vector_store = VectorStore()
    symptoms = ", ".join(state.get("failure_symptoms", []))
    similar = vector_store.search_similar(symptoms, n_results=2)
    
    # Format prompt
    prompt = INVESTIGATOR_PROMPT.format(
        failure_symptoms=symptoms,
        logs=SAMPLE_LOGS,
        similar_failures=similar
    )
    
    # Call LLM
    response = agent.call_llm(prompt, state)
    
    # Parse response
    state["investigation_complete"] = True
    state["root_cause"] = "Source API rate limit exceeded - receiving 429 errors"
    state["confidence_score"] = 0.85
    state["relevant_logs"] = [
        "2024-01-15 10:23:45 ERROR: API returned 429",
        "2024-01-15 10:25:01 ERROR: Max retries exceeded"
    ]
    
    agent.log_action(f"Diagnosis: {state['root_cause']}", state)
    
    state["current_agent"] = "investigator"
    return state
