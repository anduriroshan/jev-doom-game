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


import random
import os

# Optional temperature sampling for natural human-like variation
# 0.0 = pure argmax (default), >0.0 = sample from softmax probabilities
JEV_TEMPERATURE = float(os.environ.get("JEV_TEMPERATURE", "0.0"))


# The Choice question definition — tuned for dynamic 360-degree arena combat
ACTION_QUESTION = {
    "action": Choice(
        instructions="You are an AI agent defending the center of a circular arena in Doom. "
                     "Enemies spawn from all 360 degrees around you. You must scan around to spot enemies, AIM carefully, and SHOOT.",
        criteria={
            "ATTACK": "Shoot your weapon. ONLY choose this when an enemy is visible AND in the 'center' position on screen. Shooting when not centered wastes ammo.",
            "TURN_LEFT": "Rotate view left. Choose this when an enemy is on your left side (position is 'left' or 'far-left'), OR when NO enemies are visible (nearest_enemy_position is 'none') and you need to scan the arena for incoming threats.",
            "TURN_RIGHT": "Rotate view right. Choose this when an enemy is on your right side (position is 'right' or 'far-right').",
            "MOVE_FORWARD": "Advance forward toward a visible centered enemy when they are far away (distance > 250). DO NOT choose when no enemies are visible.",
            "MOVE_LEFT": "Strafe left to dodge incoming attacks when taking damage.",
            "MOVE_RIGHT": "Strafe right to dodge incoming attacks when taking damage.",
        },
    ),
}


def _sample_action(choice_name: str, probabilities: dict, temperature: float = 0.0) -> str:
    """Optionally sample action from probabilities with temperature, or return argmax."""
    if temperature <= 0.0 or not probabilities:
        return choice_name

    items = list(probabilities.items())
    actions = [it[0] for it in items]
    probs = [max(float(it[1]), 1e-6) for it in items]

    scaled = [p ** (1.0 / temperature) for p in probs]
    total = sum(scaled)
    if total <= 0:
        return choice_name
    norm = [s / total for s in scaled]
    return random.choices(actions, weights=norm, k=1)[0]


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
        prob_dict = dict(choice_answer.probabilities)

        # Action selection: argmax (default) or temperature sampled
        selected_action = _sample_action(choice_answer.choice, prob_dict, JEV_TEMPERATURE)

        # Jev is a classification/decision engine (System One) producing discrete
        # choices, so generative output text tokens is 0.
        # response.usage.output_tokens is preserved as api_output_tokens for reference.
        api_out = getattr(response.usage, "output_tokens", 0) or 0

        return {
            "action": selected_action,
            "confidence": choice_answer.confidence,
            "probabilities": prob_dict,
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
