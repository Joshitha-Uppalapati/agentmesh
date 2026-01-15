from datetime import datetime
from src.graph.builder import build_graph
from src.graph.state import AgentState


if __name__ == "__main__":
    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="demo_failure_pipeline",
        pipeline_config={
            "source": "s3",
            "destination": "postgres",
            "expected_schema": "v2"
        },
        retry_counts={},
        started_at=datetime.now(),
        total_llm_calls=0,
        total_cost_usd=0.0,
    )

    final_state = graph.invoke(initial_state)

    print("Demo: FAILURE → AUTO-FIX CASE")
    print(f"Final status: {final_state.get('final_status')}")
    print(f"Root cause: {final_state.get('root_cause')}")

