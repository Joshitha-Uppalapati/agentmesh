import logging
import uuid
from datetime import datetime

from dotenv import load_dotenv

from src.graph.builder import build_graph
from src.graph.state import AgentState

load_dotenv()

logger = logging.getLogger(__name__)


def run_demo_failure():
    run_id = str(uuid.uuid4())

    logger.info("run_boundary run_id=%s stage=start scenario=failure", run_id)

    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="data_ingestion_failure",
        pipeline_config={
            "source": "external_api",
            "destination": "postgres",
            "schedule": "hourly",
        },
        retry_counts={},
        started_at=datetime.utcnow(),
        total_llm_calls=0,
        total_cost_usd=0.0,
        run_id=run_id,
    )

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error("run_failed run_id=%s error=%s", run_id, str(e))
        raise

    final_state["completed_at"] = datetime.utcnow()

    logger.info(
        "metrics run_id=%s llm_calls=%d cost=%.6f",
        run_id,
        final_state.get("total_llm_calls", 0),
        final_state.get("total_cost_usd", 0.0),
    )

    logger.info("run_boundary run_id=%s stage=end scenario=failure", run_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    run_demo_failure()