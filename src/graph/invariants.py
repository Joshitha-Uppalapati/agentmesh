def assert_valid_state(state):

    for agent, count in state.get("retry_counts", {}).items():
        if count > 3:
            raise RuntimeError(f"Retry limit exceeded for {agent}")

    if state.get("final_status") is not None and state.get("current_agent") != "END":
        raise RuntimeError("Final state reached but graph did not terminate")

