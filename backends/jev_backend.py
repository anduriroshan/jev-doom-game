"""
Jev (TypeSafe System One) backend for the ViZDoom AI Benchmark.
Uses the typesafe_sdk to send game state and get structured action decisions.
"""

import time
from typesafe_sdk import Choice, TypeSafeClient


# Persistent client (reused across calls for connection pooling)
_client = None


def _get_client():
    """Lazily initialize and return a persistent TypeSafeClient."""
    global _client
    if _client is None:
        import os
        api_key = os.environ.get("TYPESAFE_API_KEY", "")
        _client = TypeSafeClient(model="jev-latest", api_key=api_key if api_key else None)
    return _client


# The Choice question definition — same for every tick
ACTION_QUESTION = {
    "action": Choice(
        instructions="You are an AI agent playing Doom. Based on the game state, pick the single best action. "
                     "IMPORTANT: You must AIM at the enemy before shooting. If the enemy is not in 'center' position, turn toward them first.",
        criteria={
            "ATTACK": "Shoot your weapon. ONLY choose this when an enemy is visible AND in the 'center' position on screen. Shooting when the enemy is off-center wastes ammo.",
            "MOVE_FORWARD": "Walk forward to get closer to enemies or explore. Choose when enemy is far away (distance > 200) or no enemies are visible.",
            "MOVE_LEFT": "Strafe left to dodge incoming fire or reposition. Good for evasive movement.",
            "MOVE_RIGHT": "Strafe right to dodge incoming fire or reposition. Good for evasive movement.",
            "TURN_LEFT": "Rotate your view LEFT. Choose this when an enemy is on your left side (position is 'far-left' or 'left') or when scanning for enemies you can't see.",
            "TURN_RIGHT": "Rotate your view RIGHT. Choose this when an enemy is on your right side (position is 'right' or 'far-right') or when scanning for enemies you can't see.",
        },
    ),
}


def get_action(state_json: str) -> dict:
    """
    Send game state to Jev and get back an action decision.

    Args:
        state_json: JSON string of the current game state.

    Returns:
        dict with keys:
            action (str): chosen action name
            confidence (float): model confidence 0-1
            probabilities (dict): probability for each action
            input_tokens (int): tokens consumed for input
            output_tokens (int): tokens produced for output
            latency_ms (float): wall-clock latency in milliseconds
            raw_response (str): raw response summary for payload size measurement
            error (str|None): error message if call failed
    """
    client = _get_client()

    start = time.perf_counter()
    try:
        response = client.system_one(
            state=state_json,
            questions=ACTION_QUESTION,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        choice_answer = response.choices["action"]

        # Jev is a classification/decision engine (System One) producing discrete
        # choices, so generative output text tokens is 0.
        # response.usage.output_tokens is preserved as api_output_tokens for reference.
        api_out = getattr(response.usage, "output_tokens", 0) or 0

        return {
            "action": choice_answer.choice,
            "confidence": choice_answer.confidence,
            "probabilities": dict(choice_answer.probabilities),
            "input_tokens": response.usage.input_tokens or 0,
            "output_tokens": 0,  # Zero generative text tokens
            "api_output_tokens": api_out,
            "latency_ms": round(elapsed_ms, 2),
            "raw_response": str(response.usage),
            "error": None,
        }

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "action": "MOVE_FORWARD",  # fallback
            "confidence": 0.0,
            "probabilities": {},
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": round(elapsed_ms, 2),
            "raw_response": "",
            "error": str(e),
        }


def cleanup():
    """Close the persistent client connection."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
