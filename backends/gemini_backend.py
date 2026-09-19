"""
Gemini Flash backend for the ViZDoom AI Benchmark.
Uses google-genai SDK with JSON output to get action decisions.
"""

import json
import time
import os
import sys

from google import genai
from google.genai import types


# Persistent client
_client = None


SYSTEM_PROMPT = (
    "You are an AI agent playing the classic video game Doom. "
    "You receive the current game state as JSON and must pick ONE action.\n\n"
    "RULES:\n"
    "- If no enemies are visible, TURN_LEFT or TURN_RIGHT to scan for enemies.\n"
    "- If an enemy is visible but NOT in 'center' position, TURN toward it first.\n"
    "- If an enemy is in 'center' position, ATTACK to shoot.\n"
    "- If enemy is far away (distance > 200), MOVE_FORWARD to get closer.\n"
    "- Strafe (MOVE_LEFT/MOVE_RIGHT) to dodge when taking damage.\n\n"
    "Available actions:\n"
    "- ATTACK: Shoot your weapon. Only effective when enemy is centered on screen.\n"
    "- MOVE_FORWARD: Walk forward.\n"
    "- MOVE_LEFT: Strafe left.\n"
    "- MOVE_RIGHT: Strafe right.\n"
    "- TURN_LEFT: Rotate view left.\n"
    "- TURN_RIGHT: Rotate view right.\n\n"
    "Respond with JSON: {\"action\": \"ACTION_NAME\", \"reasoning\": \"brief reason\"}"
)

# Valid actions for fallback validation
VALID_ACTIONS = {"ATTACK", "MOVE_FORWARD", "MOVE_LEFT", "MOVE_RIGHT", "TURN_LEFT", "TURN_RIGHT"}

# Log first error for debugging
_first_error_logged = False


def _get_client():
    """Lazily initialize and return a persistent genai Client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


def get_action(state_json: str) -> dict:
    """
    Send game state to Gemini Flash and get back an action decision.

    Returns:
        dict with action, confidence, probabilities, tokens, latency, etc.
    """
    global _first_error_logged
    client = _get_client()

    prompt = f"Current game state:\n{state_json}\n\nChoose the best action. Respond ONLY with JSON."

    start = time.perf_counter()
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Parse the JSON response
        raw_text = response.text
        parsed = json.loads(raw_text)

        action = parsed.get("action", "MOVE_FORWARD").upper().strip()
        reasoning = parsed.get("reasoning", "")

        # Validate action
        if action not in VALID_ACTIONS:
            for valid in VALID_ACTIONS:
                if valid in action:
                    action = valid
                    break
            else:
                action = "MOVE_FORWARD"

        # Extract token usage
        usage = getattr(response, "usage_metadata", None)
        input_tokens = 0
        output_tokens = 0
        if usage:
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return {
            "action": action,
            "confidence": -1.0,
            "probabilities": {},
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(elapsed_ms, 2),
            "raw_response": raw_text,
            "reasoning": reasoning,
            "error": None,
        }

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Log the first error so we can debug
        if not _first_error_logged:
            print(f"\n[GEMINI ERROR] {type(e).__name__}: {e}\n", file=sys.stderr)
            _first_error_logged = True

        return {
            "action": "MOVE_FORWARD",
            "confidence": -1.0,
            "probabilities": {},
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": round(elapsed_ms, 2),
            "raw_response": "",
            "reasoning": "",
            "error": str(e),
        }


def cleanup():
    """Cleanup."""
    global _client, _first_error_logged
    _client = None
    _first_error_logged = False
