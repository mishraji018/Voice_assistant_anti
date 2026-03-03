def run(command_text: str) -> str:
    """Standardized entry point for calculator command."""
    # Simple extraction: everything after 'calculate'
    expr = command_text.lower().replace("calculate", "").strip()
    return calculate_expr(expr)

def calculate_expr(expression):
    try:
        # Note: eval is used in original code; it's risky but preserving logic
        result = eval(expression)
        return f"The result is {result}"
    except Exception:
        return "Sorry, I couldn't calculate that."
