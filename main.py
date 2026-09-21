"""
ViZDoom AI Benchmark -- CLI Entry Point
Compare Jev (TypeSafe System One) vs Gemini 2.5 Flash playing Doom.

Usage:
    python main.py --backend jev              # Single run with Jev
    python main.py --backend gemini           # Single run with Gemini
    python main.py --backend random           # Single run with random (no API key)
    python main.py --benchmark --episodes 3   # A/B comparison (Jev vs Gemini)
"""

import argparse
import sys
import os

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich import box

from config import DEFAULT_EPISODES, DEFAULT_BACKEND, DEFAULT_SCENARIO, AVAILABLE_SCENARIOS, RECORDINGS_DIR
from game_loop import create_game, run_episode
from display import create_tick_display, print_episode_summary, console


BANNER = """
[bold bright_cyan]
  DDDD   OOO   OOO  M   M     A  I
  D   D O   O O   O MM MM    A A I
  D   D O   O O   O M M M   AAAA I
  D   D O   O O   O M   M   A  A I
  DDDD   OOO   OOO  M   M   A  A I
[/]
[bold bright_magenta]  >> Jev (System One) vs Gemini Flash -- ViZDoom Benchmark[/]
[dim]  Testing AI decision-making in real-time Doom gameplay[/]
"""


def get_backend(name):
    """Import and return the appropriate backend module."""
    if name == "jev":
        from backends import jev_backend
        return jev_backend
    elif name == "gemini":
        from backends import gemini_backend
        return gemini_backend
    elif name == "random":
        from backends import random_backend
        return random_backend
    else:
        console.print(f"[red]Unknown backend: {name}[/]")
        sys.exit(1)


def run_single(backend_name, num_episodes=1, visible=True, live_display=True, scenario=DEFAULT_SCENARIO, record_video=False):
    """Run episodes with a single backend."""
    backend = get_backend(backend_name)
    game = create_game(scenario=scenario, visible=visible)
    game.init()

    console.print(f"\n[bold]Running {num_episodes} episode(s) with [bright_cyan]{backend_name.upper()}[/] on [yellow]{scenario}[/]...\n")

    for ep_num in range(1, num_episodes + 1):
        video_file = os.path.join(RECORDINGS_DIR, f"{backend_name}_{scenario}_ep{ep_num}.mp4") if record_video else None
        if live_display:
            with Live(console=console, refresh_per_second=10, transient=True) as live:
                def display_cb(tick_data, cumulative):
                    panel = create_tick_display(tick_data, cumulative, backend_name)
                    live.update(panel)

                result = run_episode(game, backend, display_callback=display_cb, record_video=record_video, video_path=video_file)
        else:
            result = run_episode(game, backend, record_video=record_video, video_path=video_file)

        print_episode_summary(result, backend_name, ep_num)
        if result.get("video_path"):
            console.print(f"  [bright_green]🎥 Replay saved:[/] [cyan]{result['video_path']}[/]\n")

    backend.cleanup()
    game.close()


def main():
    parser = argparse.ArgumentParser(
        description="ViZDoom AI Benchmark — Jev vs Gemini Flash",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --backend random              Test with random actions (no API key needed)
  python main.py --backend jev --episodes 3    Run 3 episodes with Jev
  python main.py --backend gemini              Run 1 episode with Gemini Flash
  python main.py --benchmark --episodes 3      A/B compare: 3 episodes each (defend_the_center)
  python main.py --benchmark --scenario basic  Run on classic basic scenario
  python main.py --backend jev --headless      Run without game window
        """,
    )

    parser.add_argument(
        "--backend",
        choices=["jev", "gemini", "random"],
        default=DEFAULT_BACKEND,
        help="AI backend to use (default: random)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run A/B benchmark comparing Jev vs Gemini",
    )
    parser.add_argument(
        "--scenario",
        choices=list(AVAILABLE_SCENARIOS.keys()),
        default=DEFAULT_SCENARIO,
        help=f"ViZDoom scenario (default: {DEFAULT_SCENARIO})",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=DEFAULT_EPISODES,
        help=f"Number of episodes per backend (default: {DEFAULT_EPISODES})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without the ViZDoom game window",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable the Rich live terminal display",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record smooth 35 FPS MP4 video replay of gameplay without network lag",
    )

    args = parser.parse_args()

    # ── Print banner ──
    console.print(BANNER)

    if args.benchmark:
        # ── A/B Benchmark mode ──
        console.print(Panel(
            f"[bold]Running A/B benchmark: [bright_green]Jev[/] vs [bright_yellow]Gemini Flash[/]\n"
            f"[dim]Scenario: {args.scenario} | Episodes per backend: {args.episodes} | Recording: {'Yes (35 FPS)' if args.record else 'No'}[/]",
            border_style="bright_cyan",
            box=box.DOUBLE,
        ))

        from benchmark import run_benchmark
        run_benchmark(
            num_episodes=args.episodes,
            visible=not args.headless,
            scenario=args.scenario,
            record_video=args.record,
        )
    else:
        # ── Single backend mode ──
        run_single(
            backend_name=args.backend,
            num_episodes=args.episodes,
            visible=not args.headless,
            live_display=not args.no_display,
            scenario=args.scenario,
            record_video=args.record,
        )

    console.print("\n[bold bright_green]✓ Done![/]\n")


if __name__ == "__main__":
    main()
