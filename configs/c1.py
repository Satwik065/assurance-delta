"""C1: LLM-only. Accept if the AI's own tests pass."""
def evaluate_c1(ai_claims_tests_passed: bool) -> str:
    return "ACCEPT" if ai_claims_tests_passed else "REJECT"
