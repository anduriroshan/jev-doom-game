"""
Core game loop for the ViZDoom AI Benchmark.
Runs a single episode, collecting per-tick metrics from the selected AI backend.
"""

import os
import math
import vizdoom as vzd

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FRAME_SKIP, EPISODE_TIMEOUT,
    ACTION_MAP, ACTION_LIST, DEFAULT_SCENARIO, AVAILABLE_SCENARIOS,
)
from state_translator import translate_state


# Game variable names in the order they are added
GAME_VAR_NAMES = ["health", "ammo", "kill_count", "armor"]


def create_game(scenario=DEFAULT_SCENARIO, visible=True):
    """
    Create and configure a ViZDoom game instance.

    Args:
        scenario: Scenario name ("defend_the_center", "basic", "deadly_corridor").
        visible: If True, show the game window. If False, run headless.

    Returns:
        Configured (but not initialized) DoomGame instance.
    """
    game = vzd.DoomGame()

    # ── Load scenario config ──
    scenarios_path = os.path.join(os.path.dirname(vzd.__file__), "scenarios")
    cfg_name = AVAILABLE_SCENARIOS.get(scenario, f"{scenario}.cfg")
    cfg_path = os.path.join(scenarios_path, cfg_name)
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(scenarios_path, "defend_the_center.cfg")
    game.load_config(cfg_path)

    # ── Screen settings ──
    game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
    game.set_screen_format(vzd.ScreenFormat.RGB24)
    game.set_render_hud(True)

    # ── Window mode ──
    game.set_window_visible(visible)

    # ── Enable depth + labels buffers for state translation ──
    game.set_depth_buffer_enabled(True)
    game.set_labels_buffer_enabled(True)

    # ── Clear any pre-configured buttons and add our own ──
    game.clear_available_buttons()
    game.add_available_button(vzd.Button.ATTACK)
    game.add_available_button(vzd.Button.MOVE_FORWARD)
    game.add_available_button(vzd.Button.MOVE_LEFT)
    game.add_available_button(vzd.Button.MOVE_RIGHT)
    game.add_available_button(vzd.Button.TURN_LEFT)
    game.add_available_button(vzd.Button.TURN_RIGHT)

    # ── Game variables ──
    game.clear_available_game_variables()
    game.add_available_game_variable(vzd.GameVariable.HEALTH)
    game.add_available_game_variable(vzd.GameVariable.AMMO2)   # Pistol ammo
    game.add_available_game_variable(vzd.GameVariable.KILLCOUNT)
    game.add_available_game_variable(vzd.GameVariable.ARMOR)

    # ── Episode settings (convert decision ticks to engine tics) ──
    game.set_episode_timeout(EPISODE_TIMEOUT * FRAME_SKIP)

    # ── Mode ──
    game.set_mode(vzd.Mode.PLAYER)

    return game


def run_episode(game, backend, display_callback=None):
    """
    Run a single episode of Doom using the given AI backend.

    Args:
        game: Initialized ViZDoom game instance.
        backend: Module with get_action(state_json) → dict function.
        display_callback: Optional function called each tick with
                          (tick_data, cumulative_metrics) for live display.

    Returns:
        dict with episode-level metrics:
            ticks (int): number of AI decisions made
            total_reward (float): cumulative game reward
            kill_count (int): enemies killed
            survival_ticks (int): ticks the player survived
            final_health (int): health at end of episode
            latencies (list[float]): per-tick latency in ms
            input_tokens_total (int): total input tokens consumed
            output_tokens_total (int): total output tokens produced
            actions (list[str]): per-tick action chosen
            confidences (list[float]): per-tick confidence
            errors (int): number of API errors
            tick_data (list[dict]): full per-tick data for detailed analysis
    """
    game.new_episode()

    # ── Accumulators ──
    tick_data_list = []
    latencies = []
    actions = []
    confidences = []
    input_tokens_total = 0
    output_tokens_total = 0
    total_reward = 0.0
    errors = 0
    tick = 0

    while not game.is_episode_finished():
        state = game.get_state()
        if state is None:
            break

        # ── Translate state to JSON ──
        state_json = translate_state(state, GAME_VAR_NAMES)

        # ── Query AI backend ──
        result = backend.get_action(state_json)

        # ── Map action to ViZDoom button vector ──
        action_name = result.get("action", "MOVE_FORWARD")
        if action_name not in ACTION_MAP:
            action_name = "MOVE_FORWARD"
        action_vector = ACTION_MAP[action_name]

        # ── Execute action ──
        reward = game.make_action(action_vector, FRAME_SKIP)
        total_reward += reward

        # ── Track metrics ──
        tick += 1
        latencies.append(result["latency_ms"])
        actions.append(action_name)
        confidences.append(result.get("confidence", -1.0))
        input_tokens_total += result.get("input_tokens", 0)
        output_tokens_total += result.get("output_tokens", 0)
        if result.get("error"):
            errors += 1

        # ── Build per-tick snapshot ──
        tick_snapshot = {
            "tick": tick,
            "action": action_name,
            "confidence": result.get("confidence", -1.0),
            "probabilities": result.get("probabilities", {}),
            "latency_ms": result["latency_ms"],
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "reward": reward,
            "game_state": state_json,
            "error": result.get("error"),
            "reasoning": result.get("reasoning", ""),
        }
        tick_data_list.append(tick_snapshot)

        # ── Live display callback ──
        if display_callback:
            cumulative = {
                "tick": tick,
                "total_reward": total_reward,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "input_tokens_total": input_tokens_total,
                "output_tokens_total": output_tokens_total,
                "errors": errors,
            }
            display_callback(tick_snapshot, cumulative)

    # ── Final game state for kill count and health ──
    try:
        kill_count = int(game.get_game_variable(vzd.GameVariable.KILLCOUNT))
    except Exception:
        kill_count = 0

    try:
        final_health = max(0, int(game.get_game_variable(vzd.GameVariable.HEALTH)))
    except Exception:
        final_health = 0

    return {
        "ticks": tick,
        "total_reward": total_reward,
        "kill_count": kill_count,
        "survival_ticks": tick,
        "final_health": final_health,
        "latencies": latencies,
        "input_tokens_total": input_tokens_total,
        "output_tokens_total": output_tokens_total,
        "actions": actions,
        "confidences": confidences,
        "errors": errors,
        "tick_data": tick_data_list,
    }
