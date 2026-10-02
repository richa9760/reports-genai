from decimal import Decimal


MODEL_PRICING = {
    "openai/gpt-oss-120b": {
        "input_per_1m_tokens": Decimal("0.15"),
        "output_per_1m_tokens": Decimal("0.60"),
    },
    "openrouter/free": {
        "input_per_1m_tokens": Decimal("0"),
        "output_per_1m_tokens": Decimal("0"),
    },
}

def calculate_cost(model, input_tokens, output_tokens):
    pricing = MODEL_PRICING.get(model)

    if not pricing:
        return None, None, None

    if input_tokens is None or output_tokens is None:
        return None, None, None

    input_cost = (
        Decimal(input_tokens)
        / Decimal("1000000")
        * pricing["input_per_1m_tokens"]
    )

    output_cost = (
        Decimal(output_tokens)
        / Decimal("1000000")
        * pricing["output_per_1m_tokens"]
    )

    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost