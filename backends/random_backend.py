"""
Random action backend for testing without API keys.
Picks a random action each tick — serves as a baseline.
"""

import random
import time

from config import ACTION_LIST


def get_action(state_json: str) -> dict:
    """
    Pick a random action. Used for testing the pipeline without API keys.

    Returns:
        dict matching the same schema as jev_backend and gemini_backend.
    """
    start = time.perf_counter()

    action = random.choice(ACTION_LIST)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "action": action,
        "confidence": -1.0,
        "probabilities": {},
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": round(elapsed_ms, 4),
        "raw_response": "",
        "error": None,
    }


def cleanup():
    """No resources to clean up."""
    pass
