"""
Configuration for the ViZDoom AI Benchmark.
Manages API keys, game settings, and benchmark parameters.
"""

import os

# ──────────────────────────────────────────────
# API Keys (set via environment variables)
# ──────────────────────────────────────────────
TYPESAFE_API_KEY = os.environ.get("TYPESAFE_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ──────────────────────────────────────────────
# ViZDoom Game Settings
# ──────────────────────────────────────────────
DEFAULT_SCENARIO = "defend_the_center"
AVAILABLE_SCENARIOS = {
    "defend_the_center": "defend_the_center.cfg",
    "basic": "basic.cfg",
    "deadly_corridor": "deadly_corridor.cfg",
}

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
DEFAULT_FPS = 35        # Classic Doom native engine ticrate (35 FPS)
FRAME_SKIP = 4          # ViZDoom runs action for N internal frames per AI tick
EPISODE_TIMEOUT = 150   # Max decisions per episode (150 decisions * 4 = 600 engine tics ≈ 17s)
RECORDINGS_DIR = "recordings"

# Available actions: maps action name → ViZDoom button vector
# Order must match buttons added in game setup:
# [ATTACK, MOVE_FORWARD, MOVE_LEFT, MOVE_RIGHT, TURN_LEFT, TURN_RIGHT]
ACTION_LIST = [
    "ATTACK",
    "MOVE_FORWARD",
    "MOVE_LEFT",
    "MOVE_RIGHT",
    "TURN_LEFT",
    "TURN_RIGHT",
]

ACTION_MAP = {
    "ATTACK":       [1, 0, 0, 0, 0, 0],
    "MOVE_FORWARD": [0, 1, 0, 0, 0, 0],
    "MOVE_LEFT":    [0, 0, 1, 0, 0, 0],
    "MOVE_RIGHT":   [0, 0, 0, 1, 0, 0],
    "TURN_LEFT":    [0, 0, 0, 0, 1, 0],
    "TURN_RIGHT":   [0, 0, 0, 0, 0, 1],
}

# ──────────────────────────────────────────────
# Benchmark Settings
# ──────────────────────────────────────────────
DEFAULT_EPISODES = 3
DEFAULT_BACKEND = "random"

# ──────────────────────────────────────────────
# Estimated cost per 1M tokens (USD) — for cost comparison
# ──────────────────────────────────────────────
COST_PER_1M_INPUT = {
    "jev": 0.50,       # TypeSafe Jev estimated pricing
    "gemini": 0.15,    # Gemini Flash pricing
    "random": 0.0,
}

COST_PER_1M_OUTPUT = {
    "jev": 1.50,       # TypeSafe Jev estimated pricing
    "gemini": 0.60,    # Gemini Flash pricing
    "random": 0.0,
}

