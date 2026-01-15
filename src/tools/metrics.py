def log_metrics(state):
    print(
        f"[metrics] pipeline={state.get('pipeline_id')} "
        f"llm_calls={state.get('total_llm_calls')} "
        f"cost=${state.get('total_cost_usd')} "
        f"duration={state.get('completed_at')}"
    )
