"""
Translates ViZDoom game state into a JSON string for AI backends.
Extracts health, ammo, armor, kill count, enemy detection via labels buffer,
and distance estimation via depth buffer.
"""

import json
import numpy as np


# Enemy object names in ViZDoom (common across scenarios)
ENEMY_NAMES = {
    "Cacodemon", "DoomPlayer", "HellKnight", "Baron", "Imp",
    "Demon", "Spectre", "Revenant", "Mancubus", "Arachnotron",
    "Archvile", "SpiderMastermind", "Cyberdemon", "Zombieman",
    "ShotgunGuy", "ChaingunGuy", "LostSoul", "PainElemental",
    "WolfensteinSS", "CommanderKeen",
    # ViZDoom basic scenario uses a single monster
    "MarineChainsawVzd",
}


def translate_state(state, game_variables_order):
    """
    Convert a ViZDoom GameState object into a JSON string.

    Args:
        state: ViZDoom state object (from game.get_state())
        game_variables_order: list of variable names in order they appear
                              in state.game_variables

    Returns:
        JSON string representing the game state, or None if state is None.
    """
    if state is None:
        return None

    # ── Extract game variables ──
    gv = {}
    for i, name in enumerate(game_variables_order):
        if i < len(state.game_variables):
            gv[name] = int(state.game_variables[i])

    # ── Enemy detection via labels ──
    enemies = []
    if hasattr(state, "labels") and state.labels is not None:
        for label in state.labels:
            # In ViZDoom basic scenario, enemies have object_name not matching player
            name = getattr(label, "object_name", "")
            # Filter: anything that's not a wall/floor/ceiling decoration is likely enemy
            # In basic.cfg the monster is the only labeled object
            if name and name not in ("DoomPlayer",):
                enemy_info = {
                    "name": name,
                    "x": int(getattr(label, "x", 0)),
                    "y": int(getattr(label, "y", 0)),
                    "width": int(getattr(label, "width", 0)),
                    "height": int(getattr(label, "height", 0)),
                }
                # Estimate distance via depth buffer
                if (
                    hasattr(state, "depth_buffer")
                    and state.depth_buffer is not None
                ):
                    cx = enemy_info["x"] + enemy_info["width"] // 2
                    cy = enemy_info["y"] + enemy_info["height"] // 2
                    db = state.depth_buffer
                    if 0 <= cy < db.shape[0] and 0 <= cx < db.shape[1]:
                        enemy_info["distance"] = round(float(db[cy, cx]), 1)

                # Relative position (where is enemy on screen?)
                screen_w = state.screen_buffer.shape[1] if state.screen_buffer is not None else 640
                center_x = enemy_info["x"] + enemy_info["width"] // 2
                ratio = center_x / max(screen_w, 1)
                if ratio < 0.25:
                    enemy_info["position"] = "far-left"
                elif ratio < 0.4:
                    enemy_info["position"] = "left"
                elif ratio < 0.6:
                    enemy_info["position"] = "center"
                elif ratio < 0.75:
                    enemy_info["position"] = "right"
                else:
                    enemy_info["position"] = "far-right"

                enemies.append(enemy_info)

    # ── Build state dict ──
    state_dict = {
        "health": gv.get("health", 100),
        "armor": gv.get("armor", 0),
        "ammo": gv.get("ammo", 26),
        "kill_count": gv.get("kill_count", 0),
        "enemies_visible": len(enemies) > 0,
        "enemy_count": len(enemies),
    }

    if enemies:
        # Sort by distance (closest first)
        enemies_with_dist = [e for e in enemies if "distance" in e]
        if enemies_with_dist:
            enemies_with_dist.sort(key=lambda e: e["distance"])
            nearest = enemies_with_dist[0]
            state_dict["nearest_enemy_distance"] = nearest["distance"]
            state_dict["nearest_enemy_position"] = nearest.get("position", "unknown")
        elif enemies:
            # No depth info, use screen position
            state_dict["nearest_enemy_position"] = enemies[0].get("position", "unknown")
    else:
        state_dict["nearest_enemy_distance"] = None
        state_dict["nearest_enemy_position"] = "none"

    return json.dumps(state_dict)
