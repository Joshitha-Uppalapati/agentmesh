import logging

from langgraph.graph import END, StateGraph

from src.tools.escalation import escalate_to_human
from src.agents.fixer import fixer_agent
from src.agents.investigator import investigator_agent
from src.agents.monitor import monitor_agent
from src.agents.validator import validator_agent
from src.graph.router import route_after_validation, should_investigate, should_retry_fix
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


def build_graph():
    logger.info("building_langgraph_workflow")

    workflow = StateGraph(AgentState)

    workflow.add_node("monitor", monitor_agent)
    workflow.add_node("investigator", investigator_agent)
    workflow.add_node("fixer", fixer_agent)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("escalate", escalate_to_human)

    workflow.set_entry_point("monitor")

    workflow.add_conditional_edges(
        "monitor",
        should_investigate,
        {
            "healthy": END,
            "investigate": "investigator",
        },
    )

    workflow.add_edge("investigator", "fixer")

    workflow.add_conditional_edges(
        "fixer",
        should_retry_fix,
        {
            "validate": "validator",
            "retry": "investigator",
            "escalate": "escalate",
        },
    )

    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "approved": END,
            "retry_fix": "fixer",
            "escalate": "escalate",
        },
    )

    workflow.add_edge("escalate", END)

    logger.info("graph_compiled_successfully")

    return workflow.compile()