"""
A/B Benchmark runner for the ViZDoom AI Benchmark.
Runs multiple episodes per backend, aggregates metrics, and displays comparison.
"""

import json
import math
import os
import time
from collections import Counter
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich import box

from config import ACTION_LIST, COST_PER_1M_INPUT, COST_PER_1M_OUTPUT, DEFAULT_SCENARIO
from game_loop import create_game, run_episode
from display import print_episode_summary


console = Console()


def compute_entropy(counts_dict, total):
    """Compute Shannon entropy of a distribution."""
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts_dict.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def aggregate_metrics(episodes_data, backend_name):
    """
    Aggregate metrics across multiple episodes.

    Args:
        episodes_data: list of episode result dicts
        backend_name: "jev", "gemini", or "random"

    Returns:
        dict with aggregated metrics.
    """
    if not episodes_data:
        return {}

    all_latencies = []
    all_actions = []
    all_confidences = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_ticks = 0
    total_kills = 0
    total_errors = 0
    survival_ticks = []
    rewards = []

    for ep in episodes_data:
        all_latencies.extend(ep["latencies"])
        all_actions.extend(ep["actions"])
        all_confidences.extend([c for c in ep["confidences"] if c >= 0])
        total_input_tokens += ep["input_tokens_total"]
        total_output_tokens += ep["output_tokens_total"]
        total_ticks += ep["ticks"]
        total_kills += ep["kill_count"]
        total_errors += ep["errors"]
        survival_ticks.append(ep["survival_ticks"])
        rewards.append(ep["total_reward"])

    # Latency percentiles
    sorted_lat = sorted(all_latencies) if all_latencies else [0]
    n = len(sorted_lat)

    # Action distribution
    action_counts = Counter(all_actions)
    action_total = sum(action_counts.values())

    # Cost estimates
    input_cost = (total_input_tokens / 1_000_000) * COST_PER_1M_INPUT.get(backend_name, 0)
    output_cost = (total_output_tokens / 1_000_000) * COST_PER_1M_OUTPUT.get(backend_name, 0)

    metrics = {
        "backend": backend_name,
        "episodes": len(episodes_data),
        "total_ticks": total_ticks,
        "total_kills": total_kills,
        "avg_kills": total_kills / len(episodes_data),
        "avg_survival_ticks": sum(survival_ticks) / len(survival_ticks),
        "avg_reward": sum(rewards) / len(rewards),

        # Latency
        "avg_latency_ms": sum(sorted_lat) / n,
        "p50_latency_ms": sorted_lat[n // 2],
        "p95_latency_ms": sorted_lat[int(n * 0.95)] if n > 1 else sorted_lat[0],
        "p99_latency_ms": sorted_lat[int(n * 0.99)] if n > 1 else sorted_lat[0],
        "min_latency_ms": sorted_lat[0],
        "max_latency_ms": sorted_lat[-1],

        # Tokens
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "avg_input_tokens_per_tick": total_input_tokens / max(total_ticks, 1),
        "avg_output_tokens_per_tick": total_output_tokens / max(total_ticks, 1),

        # Throughput
        "decisions_per_second": 1000.0 / (sum(sorted_lat) / n) if sorted_lat and sorted_lat[0] > 0 else 0,

        # Cost
        "total_cost_usd": input_cost + output_cost,
        "cost_per_decision_usd": (input_cost + output_cost) / max(total_ticks, 1),

        # Confidence (Jev-specific)
        "avg_confidence": sum(all_confidences) / len(all_confidences) if all_confidences else -1,

        # Action diversity (Shannon entropy)
        "action_entropy": compute_entropy(action_counts, action_total),
        "action_distribution": {a: action_counts.get(a, 0) / max(action_total, 1) for a in ACTION_LIST},

        # Errors
        "total_errors": total_errors,
        "error_rate": total_errors / max(total_ticks, 1),

        # Response payload
        "avg_response_bytes": 0,  # Will be computed if raw_response data is available
    }

    return metrics


def print_comparison_table(jev_metrics, gemini_metrics, scenario=DEFAULT_SCENARIO):
    """Print a side-by-side comparison table."""
    table = Table(
        title=f"⚔️  JEV vs GEMINI FLASH — BENCHMARK RESULTS ({scenario})",
        box=box.DOUBLE_EDGE,
        border_style="bright_cyan",
        title_style="bold bright_magenta",
        header_style="bold bright_white on dark_blue",
    )
    table.add_column("Metric", style="bold white", width=30)
    table.add_column("Jev (System One)", justify="right", style="bright_green", width=20)
    table.add_column("Gemini Flash", justify="right", style="bright_yellow", width=20)
    table.add_column("Winner", justify="center", width=12)

    def add_metric(label, key, lower_is_better=True, format_str="{}", skip_if_neg=False):
        jv = jev_metrics.get(key)
        gv = gemini_metrics.get(key)

        if jv is None and gv is None:
            return

        # Handle formatting
        if skip_if_neg and (jv is None or jv < 0) and (gv is None or gv < 0):
            return

        jv_str = format_str.format(jv) if jv is not None and (not skip_if_neg or jv >= 0) else "N/A"
        gv_str = format_str.format(gv) if gv is not None and (not skip_if_neg or gv >= 0) else "N/A"

        # Determine winner
        winner = "—"
        if jv is not None and gv is not None and jv != gv:
            if skip_if_neg and (jv < 0 or gv < 0):
                winner = "—"
            elif lower_is_better:
                winner = "[green]🟢 Jev[/]" if jv < gv else "[yellow]🟡 Gemini[/]"
            else:
                winner = "[green]🟢 Jev[/]" if jv > gv else "[yellow]🟡 Gemini[/]"
        elif jv == gv and jv is not None:
            winner = "[dim]Tie[/]"

        table.add_row(label, jv_str, gv_str, winner)

    # ── Performance ──
    table.add_row("[bold cyan]═══ PERFORMANCE ═══", "", "", "", style="dim")
    add_metric("Avg latency (ms)", "avg_latency_ms", lower_is_better=True, format_str="{:.1f}")
    add_metric("p50 latency (ms)", "p50_latency_ms", lower_is_better=True, format_str="{:.1f}")
    add_metric("p95 latency (ms)", "p95_latency_ms", lower_is_better=True, format_str="{:.1f}")
    add_metric("p99 latency (ms)", "p99_latency_ms", lower_is_better=True, format_str="{:.1f}")
    add_metric("Decisions/second", "decisions_per_second", lower_is_better=False, format_str="{:.2f}")

    # ── Token usage ──
    table.add_row("[bold cyan]═══ TOKEN USAGE ═══", "", "", "", style="dim")
    add_metric("Input tokens (total)", "total_input_tokens", lower_is_better=True, format_str="{:,.0f}")
    add_metric("Output tokens (total)", "total_output_tokens", lower_is_better=True, format_str="{:,.0f}")
    add_metric("Avg input tokens/tick", "avg_input_tokens_per_tick", lower_is_better=True, format_str="{:.0f}")
    add_metric("Avg output tokens/tick", "avg_output_tokens_per_tick", lower_is_better=True, format_str="{:.0f}")

    # ── Cost ──
    table.add_row("[bold cyan]═══ COST ═══", "", "", "", style="dim")
    add_metric("Total cost (USD)", "total_cost_usd", lower_is_better=True, format_str="${:.6f}")
    add_metric("Cost per decision (USD)", "cost_per_decision_usd", lower_is_better=True, format_str="${:.8f}")

    # ── Gameplay ──
    table.add_row("[bold cyan]═══ GAMEPLAY ═══", "", "", "", style="dim")
    add_metric("Avg kills/episode", "avg_kills", lower_is_better=False, format_str="{:.1f}")
    add_metric("Avg survival (ticks)", "avg_survival_ticks", lower_is_better=False, format_str="{:.0f}")
    add_metric("Avg reward", "avg_reward", lower_is_better=False, format_str="{:.1f}")

    # ── Decision quality ──
    table.add_row("[bold cyan]═══ DECISION QUALITY ═══", "", "", "", style="dim")
    add_metric("Avg confidence", "avg_confidence", lower_is_better=False, format_str="{:.3f}", skip_if_neg=True)
    add_metric("Action entropy", "action_entropy", lower_is_better=False, format_str="{:.3f}")
    add_metric("Error rate", "error_rate", lower_is_better=True, format_str="{:.2%}")

    # ── Action distribution ──
    table.add_row("[bold cyan]═══ ACTION DISTRIBUTION ═══", "", "", "", style="dim")
    for action in ACTION_LIST:
        jv = jev_metrics.get("action_distribution", {}).get(action, 0)
        gv = gemini_metrics.get("action_distribution", {}).get(action, 0)
        table.add_row(f"  → {action}", f"{jv:.1%}", f"{gv:.1%}", "")

    console.print()
    console.print(table)
    console.print()


def run_benchmark(num_episodes=3, visible=True, scenario=DEFAULT_SCENARIO):
    """
    Run a full A/B benchmark comparing Jev and Gemini.

    Args:
        num_episodes: number of episodes to run per backend
        visible: whether to show the ViZDoom window
        scenario: scenario name ("defend_the_center", "basic", "deadly_corridor")

    Returns:
        (jev_metrics, gemini_metrics) tuple of aggregated metric dicts
    """
    from backends import jev_backend, gemini_backend

    game = create_game(scenario=scenario, visible=visible)
    game.init()

    results = {}

    for backend_name, backend in [("jev", jev_backend), ("gemini", gemini_backend)]:
        console.print(f"\n[bold bright_cyan]{'='*50}")
        console.print(f"[bold bright_cyan]  Running {num_episodes} episodes with {backend_name.upper()} [{scenario}]")
        console.print(f"[bold bright_cyan]{'='*50}\n")

        episodes = []
        for ep_num in range(1, num_episodes + 1):
            console.print(f"[dim]  Episode {ep_num}/{num_episodes}...[/]")

            ep_result = run_episode(game, backend)
            episodes.append(ep_result)

            print_episode_summary(ep_result, backend_name, ep_num)

        results[backend_name] = episodes
        backend.cleanup()

    game.close()

    # ── Aggregate & compare ──
    jev_metrics = aggregate_metrics(results["jev"], "jev")
    gemini_metrics = aggregate_metrics(results["gemini"], "gemini")

    print_comparison_table(jev_metrics, gemini_metrics, scenario=scenario)

    # ── Save results to JSON ──
    output = {
        "timestamp": datetime.now().isoformat(),
        "scenario": scenario,
        "episodes_per_backend": num_episodes,
        "jev": jev_metrics,
        "gemini": gemini_metrics,
    }
    # Convert non-serializable values
    for key in output:
        if isinstance(output[key], dict):
            for k, v in output[key].items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    output[key][k] = str(v)

    results_path = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    console.print(f"[dim]Results saved to {results_path}[/]")

    return jev_metrics, gemini_metrics
