import logging
import uuid
from datetime import UTC, datetime

from dotenv import load_dotenv

from src.graph.builder import build_graph
from src.graph.state import AgentState

load_dotenv()

logger = logging.getLogger(__name__)


def run_demo():
    run_id = str(uuid.uuid4())

    logger.info("run_boundary run_id=%s stage=start", run_id)
    logger.info("agentmesh_run_started run_id=%s", run_id)

    logger.info("building_graph run_id=%s", run_id)
    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="data_ingestion_prod",
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
    )

    logger.info(
        "run_started run_id=%s pipeline=%s",
        run_id,
        initial_state["pipeline_id"],
    )

    try:
        final_state = graph.invoke(initial_state)
    except Exception as error:
        logger.error("run_failed run_id=%s error=%s", run_id, str(error))
        raise

    final_state["completed_at"] = datetime.now(UTC)

    logger.info("run_boundary run_id=%s stage=results", run_id)
    logger.info("run_completed run_id=%s", run_id)

    logger.info(
        "final_status run_id=%s status=%s health=%s",
        run_id,
        final_state.get("final_status", "unknown"),
        final_state.get("health_status", "unknown"),
    )

    if final_state.get("root_cause"):
        logger.info(
            "root_cause run_id=%s cause=%s confidence=%.2f",
            run_id,
            final_state["root_cause"],
            final_state.get("confidence_score", 0.0),
        )

    if final_state.get("proposed_fix"):
        logger.info(
            "proposed_fix run_id=%s fix=%s type=%s validation=%s",
            run_id,
            final_state["proposed_fix"],
            final_state.get("fix_type", "unknown"),
            final_state.get("validation_result", "pending"),
        )

    completed = final_state["completed_at"]
    started = final_state.get("started_at", completed)
    duration = (completed - started).total_seconds()

    logger.info(
        "metrics run_id=%s llm_calls=%d cost=%.6f duration=%.2fs",
        run_id,
        final_state.get("total_llm_calls", 0),
        final_state.get("total_cost_usd", 0.0),
        duration,
    )

    logger.info("run_boundary run_id=%s stage=end", run_id)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    run_demo()