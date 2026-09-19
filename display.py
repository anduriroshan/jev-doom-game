"""
Rich terminal dashboard for real-time game state and AI decision display.
"""

import sys
import os
import math
from collections import Counter

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich import box


console = Console()


def create_tick_display(tick_data, cumulative, backend_name="unknown"):
    """
    Create a Rich renderable showing the current game tick state.

    Args:
        tick_data: dict from the current tick (action, confidence, latency, etc.)
        cumulative: dict with running totals (tick, avg_latency, tokens, etc.)
        backend_name: name of the active AI backend

    Returns:
        Rich Panel renderable.
    """
    import json
    game_state = json.loads(tick_data["game_state"]) if tick_data.get("game_state") else {}

    # ── Header ──
    header = Text()
    header.append("🎮 DOOM AI BENCHMARK", style="bold cyan")
    header.append(f"  —  Backend: ", style="dim")
    header.append(backend_name.upper(), style="bold magenta")

    # ── Game State Panel ──
    health = game_state.get("health", 0)
    health_color = "green" if health > 50 else "yellow" if health > 25 else "red"
    ammo = game_state.get("ammo", 0)
    armor = game_state.get("armor", 0)
    kills = game_state.get("kill_count", 0)

    state_text = Text()
    state_text.append(f"  ❤️  Health: ", style="dim")
    state_text.append(f"{health}", style=f"bold {health_color}")
    state_text.append(f"   🛡️  Armor: ", style="dim")
    state_text.append(f"{armor}", style="bold blue")
    state_text.append(f"\n  🔫 Ammo: ", style="dim")
    state_text.append(f"{ammo}", style="bold yellow")
    state_text.append(f"     💀 Kills: ", style="dim")
    state_text.append(f"{kills}", style="bold red")

    # ── Enemy Info ──
    enemy_text = Text()
    enemies_visible = game_state.get("enemies_visible", False)
    enemy_count = game_state.get("enemy_count", 0)
    if enemies_visible:
        enemy_text.append(f"  👁️  Enemies: ", style="dim")
        enemy_text.append(f"{enemy_count} visible", style="bold red")
        dist = game_state.get("nearest_enemy_distance")
        pos = game_state.get("nearest_enemy_position", "unknown")
        if dist is not None:
            enemy_text.append(f"\n  📏 Nearest: ", style="dim")
            enemy_text.append(f"{dist} units", style="bold")
            enemy_text.append(f" ({pos})", style="cyan")
        else:
            enemy_text.append(f"\n  📏 Position: ", style="dim")
            enemy_text.append(pos, style="cyan")
    else:
        enemy_text.append("  👁️  No enemies visible", style="dim yellow")

    # ── AI Decision ──
    decision_text = Text()
    action = tick_data.get("action", "?")
    confidence = tick_data.get("confidence", -1)
    latency = tick_data.get("latency_ms", 0)

    action_emoji = {
        "ATTACK": "🔥",
        "MOVE_FORWARD": "⬆️ ",
        "MOVE_LEFT": "⬅️ ",
        "MOVE_RIGHT": "➡️ ",
        "TURN_LEFT": "↩️ ",
        "TURN_RIGHT": "↪️ ",
    }

    decision_text.append(f"  {action_emoji.get(action, '❓')} Decision: ", style="dim")
    decision_text.append(action, style="bold green")
    if confidence >= 0:
        conf_color = "green" if confidence > 0.7 else "yellow" if confidence > 0.4 else "red"
        decision_text.append(f" ({confidence:.1%})", style=f"bold {conf_color}")

    decision_text.append(f"\n  ⏱️  Latency: ", style="dim")
    lat_color = "green" if latency < 200 else "yellow" if latency < 500 else "red"
    decision_text.append(f"{latency:.0f}ms", style=f"bold {lat_color}")

    avg_lat = cumulative.get("avg_latency", 0)
    decision_text.append(f"   📊 Avg: ", style="dim")
    decision_text.append(f"{avg_lat:.0f}ms", style="bold")

    # ── Probabilities bar (if available) ──
    probs = tick_data.get("probabilities", {})
    prob_text = Text()
    if probs:
        prob_text.append("  📈 Probabilities:\n", style="dim")
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        for name, prob in sorted_probs:
            bar_len = int(prob * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            prob_text.append(f"     {name:<14} ", style="dim")
            prob_text.append(bar, style="cyan")
            prob_text.append(f" {prob:.1%}\n", style="bold")

    # ── Token usage ──
    token_text = Text()
    token_text.append(f"  📥 Input tokens: ", style="dim")
    token_text.append(f"{cumulative.get('input_tokens_total', 0):,}", style="bold cyan")
    token_text.append(f"   📤 Output tokens: ", style="dim")
    token_text.append(f"{cumulative.get('output_tokens_total', 0):,}", style="bold cyan")
    token_text.append(f"\n  🔄 Tick: ", style="dim")
    token_text.append(f"{cumulative.get('tick', 0)}", style="bold")
    if cumulative.get("errors", 0) > 0:
        token_text.append(f"   ⚠️  Errors: ", style="dim")
        token_text.append(f"{cumulative['errors']}", style="bold red")

    # ── Reasoning (Gemini only) ──
    reasoning = tick_data.get("reasoning", "")
    reasoning_text = Text()
    if reasoning:
        reasoning_text.append(f"  💭 ", style="dim")
        reasoning_text.append(reasoning[:80], style="italic dim cyan")

    # ── Assemble ──
    content = Text()
    content.append_text(header)
    content.append("\n")
    content.append("─" * 50 + "\n", style="dim")
    content.append_text(state_text)
    content.append("\n")
    content.append("─" * 50 + "\n", style="dim")
    content.append_text(enemy_text)
    content.append("\n")
    content.append("─" * 50 + "\n", style="dim")
    content.append_text(decision_text)
    content.append("\n")
    if probs:
        content.append("─" * 50 + "\n", style="dim")
        content.append_text(prob_text)
    content.append("─" * 50 + "\n", style="dim")
    content.append_text(token_text)
    if reasoning:
        content.append("\n")
        content.append_text(reasoning_text)

    return Panel(
        content,
        border_style="bright_cyan",
        box=box.DOUBLE,
        title="[bold bright_green]◈ LIVE[/]",
        subtitle=f"[dim]Tick {cumulative.get('tick', 0)}[/]",
    )


def print_episode_summary(episode_result, backend_name, episode_num):
    """Print a summary table for a completed episode."""
    r = episode_result

    table = Table(
        title=f"Episode {episode_num} — {backend_name.upper()}",
        box=box.ROUNDED,
        border_style="cyan",
        title_style="bold magenta",
    )
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Ticks survived", str(r["ticks"]))
    table.add_row("Kill count", str(r["kill_count"]))
    table.add_row("Final health", str(r["final_health"]))
    table.add_row("Total reward", f"{r['total_reward']:.1f}")

    if r["latencies"]:
        sorted_lat = sorted(r["latencies"])
        table.add_row("Avg latency (ms)", f"{sum(sorted_lat)/len(sorted_lat):.1f}")
        table.add_row("p50 latency (ms)", f"{sorted_lat[len(sorted_lat)//2]:.1f}")
        p95_idx = int(len(sorted_lat) * 0.95)
        table.add_row("p95 latency (ms)", f"{sorted_lat[min(p95_idx, len(sorted_lat)-1)]:.1f}")

    table.add_row("Input tokens (total)", f"{r['input_tokens_total']:,}")
    table.add_row("Output tokens (total)", f"{r['output_tokens_total']:,}")
    table.add_row("API errors", str(r["errors"]))

    # Action distribution
    action_counts = Counter(r["actions"])
    for action in sorted(action_counts.keys()):
        pct = action_counts[action] / max(len(r["actions"]), 1) * 100
        table.add_row(f"  → {action}", f"{action_counts[action]} ({pct:.0f}%)")

    console.print(table)
    console.print()
