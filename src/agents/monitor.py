from src.agents.base import BaseAgent
from src.prompts.templates import MONITOR_PROMPT
from src.graph.state import AgentState
from datetime import datetime


def monitor_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Monitor")
    agent.log_action("Starting health check", state)
    
    # Format prompt with state data
    prompt = MONITOR_PROMPT.format(
        pipeline_id=state.get("pipeline_id", "unknown"),
        pipeline_config=state.get("pipeline_config", {}),
        last_run_time="6 hours ago",  # Mock data
        current_status="ERROR",
        error_count=5
    )
    
    # Call LLM
    response = agent.call_llm(prompt, state)
    
    if "failed" in response.lower():
        state["health_status"] = "failed"
        state["failure_detected"] = True
        state["failure_timestamp"] = datetime.now()
        state["failure_symptoms"] = [
            "Missing data in target table",
            "Last successful run was 6 hours ago"
        ]
        agent.log_action("FAILURE DETECTED", state)
    else:
        state["health_status"] = "healthy"
        state["failure_detected"] = False
        agent.log_action("System healthy", state)
    
    state["current_agent"] = "monitor"
    return state
