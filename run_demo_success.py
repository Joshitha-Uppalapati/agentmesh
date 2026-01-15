from datetime import datetime
from src.graph.builder import build_graph
from src.graph.state import AgentState


if __name__ == "__main__":
    graph = build_graph()

    initial_state = AgentState(
        pipeline_id="demo_success_pipeline",
        pipeline_config={
            "source": "s3",
            "destination": "postgres",
            "expected_behavior": "healthy"
        },
        retry_counts={},
        started_at=datetime.now(),
        total_llm_calls=0,
        total_cost_usd=0.0,
    )

    final_state = graph.invoke(initial_state)

    print("Demo: SUCCESS CASE")
    print(f"Final status: {final_state.get('final_status')}")
