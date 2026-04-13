import logging
import os
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def escalate_to_human(state: dict) -> dict:
    log_path = "data/escalations.log"

    # First run on a fresh machine should not die because a directory is missing.
    os.makedirs("data", exist_ok=True)

    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(
                f"{datetime.now(UTC).isoformat()} | "
                f"run_id={state.get('run_id')} | "
                f"pipeline_id={state.get('pipeline_id')} | "
                f"root_cause={state.get('root_cause')} | "
                f"proposed_fix={state.get('proposed_fix')} | "
                f"confidence={state.get('confidence_score')}\n"
            )
    except Exception as error:
        logger.warning("failed_to_persist_escalation_log error=%s", str(error))
        raise

    state["final_status"] = "escalated"
    return state