from datetime import datetime
from src.graph.builder import build_graph
from src.graph.state import AgentState


def test_graph_runs_without_error():
    """
    Basic smoke test.
    """

    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="test_pipeline",
        pipeline_config={"source": "test", "destination": "test"},
        retry_counts={},
        started_at=datetime.now(),
        total_llm_calls=0,
        total_cost_usd=0.0,
    )

    final_state = graph.invoke(initial_state)

    assert final_state is not None
    assert "final_status" in final_state

