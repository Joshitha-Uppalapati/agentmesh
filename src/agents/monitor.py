from datetime import UTC, datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.graph.state import AgentState
from src.prompts.templates import MONITOR_PROMPT


class MonitorResult(BaseModel):
    health_status: Literal["healthy", "degraded", "failed"]
    failure_detected: bool
    failure_symptoms: List[str] = Field(default_factory=list)


def _build_monitor_fallback() -> MonitorResult:
    # Keep the fallback boring and deterministic. The monitor's job is to route
    # the graph, not to show off.
    return MonitorResult(
        health_status="failed",
        failure_detected=True,
        failure_symptoms=[
            "Missing data in target table",
            "Last successful run was 6 hours ago",
        ],
    )


def monitor_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Monitor")
    agent.log_action("Health check", state)

    prompt = MONITOR_PROMPT.format(
        pipeline_id=state.get("pipeline_id", "unknown"),
        pipeline_config=state.get("pipeline_config", {}),
        # hardcoded for demo — in prod this should come from scheduler metadata.
        last_run_time="6 hours ago",
        current_status="ERROR",
        error_count=5,
    )

    result = agent.invoke_structured(
        MonitorResult,
        prompt,
        state,
        fallback_fn=_build_monitor_fallback,
    )

    state["health_status"] = result.health_status
    state["failure_detected"] = result.failure_detected
    state["failure_symptoms"] = result.failure_symptoms
    state["failure_timestamp"] = datetime.now(UTC) if result.failure_detected else None
    state["current_agent"] = "monitor"

    if result.failure_detected:
        agent.log_action(f"Failure detected: status={result.health_status}", state)
    else:
        agent.log_action("System healthy", state)

    return state