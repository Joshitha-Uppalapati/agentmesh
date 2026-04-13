import logging
import uuid
from datetime import UTC, datetime

from src.graph.builder import build_graph
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


def run_demo():
    run_id = str(uuid.uuid4())

    logger.info("run_boundary run_id=%s stage=start", run_id)

    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="data_ingestion_escalation",
        pipeline_config={
            "source": "external_api",
            "destination": "postgres",
            "schedule": "hourly",
        },
        retry_counts={},
        started_at=datetime.now(UTC),
        total_llm_calls=0,
        total_cost_usd=0.0,
        run_id=run_id,
        force_escalation=True,
    )

    final_state = graph.invoke(initial_state)

    logger.info(
        "final_status run_id=%s status=%s",
        run_id,
        final_state.get("final_status"),
    )

    logger.info("run_boundary run_id=%s stage=end", run_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_demo()