# ViZDoom AI Agent

An AI agent framework for **ViZDoom** (Doom reinforcement learning & research platform). The system translates in-game visual and tactical state into structured JSON, queries an AI backend (such as **Jev / TypeSafe System One**, **Gemini Flash**, or a **Random** baseline) in real-time, displays live terminal telemetry using Rich, and records smooth 35 FPS MP4 video replays.

---

## Requirements & Prerequisites

### System Requirements
- **Python**: Python 3.9, 3.10, 3.11, or 3.12
- **Operating System**: 
  - **Windows**: Windows 10 or 11 (64-bit)
  - **Linux**: Ubuntu 20.04+, Debian 11+, Fedora, Arch Linux, or Docker (GUI or Headless)

### API Keys
Depending on which AI backend you want to run:
- **Random Baseline**: No API key required.
- **Jev (TypeSafe System One)**: Requires a `TYPESAFE_API_KEY`.
- **Gemini Flash**: Requires a `GEMINI_API_KEY` (Google GenAI).

### Python Dependencies (`requirements.txt`)
- `vizdoom>=1.2.4` — ViZDoom Doom game environment and renderer
- `typesafe-sdk` — SDK for Jev System One structured decisions
- `google-genai` — SDK for Gemini Flash backend
- `rich` — Terminal formatting, dashboards, and live progress display
- `numpy` — Array manipulation for game frame buffers
- `imageio` & `imageio-ffmpeg` — Frame encoding and MP4 replay export

---

## Installation Guide

### Windows Setup

1. **Clone or download the repository**:
   ```cmd
   git clone <repo-url>
   cd jev-test
   ```

2. **Create a virtual environment**:
   ```cmd
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - In **PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
     *(If script execution is disabled, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first)*
   - In **Command Prompt (cmd)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```

4. **Install required dependencies**:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Set Environment Variables**:
   - In **PowerShell**:
     ```powershell
     $env:TYPESAFE_API_KEY="your_typesafe_api_key_here"
     $env:GEMINI_API_KEY="your_gemini_api_key_here"  # Optional
     ```
   - In **Command Prompt**:
     ```cmd
     set TYPESAFE_API_KEY=your_typesafe_api_key_here
     set GEMINI_API_KEY=your_gemini_api_key_here
     ```

---

### Linux Setup

1. **Install System Dependencies (Ubuntu / Debian)**:
   ViZDoom requires standard build tools and audio/video development libraries:
   ```bash
   sudo apt-get update && sudo apt-get install -y \
       build-essential \
       zlib1g-dev \
       libsdl2-dev \
       libopenal-dev
   ```

2. **Clone or navigate to the repository**:
   ```bash
   cd jev-test
   ```

3. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Set Environment Variables**:
   ```bash
   export TYPESAFE_API_KEY="your_typesafe_api_key_here"
   export GEMINI_API_KEY="your_gemini_api_key_here"  # Optional
   ```

---

## Steps to Test and Verify

Follow these quick verification steps to confirm that your environment, ViZDoom, and video recording are working properly.

### 1. Test Without API Keys (Random Baseline)
Run a quick test episode using the random action backend. This verifies the ViZDoom engine, window display, and live Rich terminal telemetry without needing any API key:
```bash
# Windows / Linux Desktop (with game window)
python main.py --backend random
```

### 2. Test Video Replay Recording
Test that ViZDoom frame buffers are captured and saved to MP4 format via `imageio`:
```bash
python main.py --backend random --record
```
After the episode ends, verify the replay file was generated:
```
recordings/random_defend_the_center_ep1.mp4
```

### 3. Test Headless Execution (Recommended for Servers & Cloud Instances)
If you are running on an SSH server, Docker container, or cloud instance without a monitor, run with the `--headless` flag:
```bash
python main.py --backend random --headless --record
```
*(On minimal Linux containers without X11, you can also prepend `SDL_VIDEODRIVER=dummy` if prompted).*

### 4. Test with Jev (TypeSafe System One)
Once `TYPESAFE_API_KEY` is configured, test Jev running live gameplay:
```bash
# 1 episode with live window and replay recording
python main.py --backend jev --record

# 3 episodes with custom scenario
python main.py --backend jev --episodes 3 --scenario defend_the_center --record
```

---

## CLI Options Reference

| Argument | Choices / Type | Default | Description |
|---|---|---|---|
| `--backend` | `jev`, `gemini`, `random` | `random` | Selected AI decision backend |
| `--episodes` | Integer | `1` | Number of game episodes to run |
| `--scenario` | `defend_the_center`, `basic`, `deadly_corridor` | `defend_the_center` | ViZDoom scenario map |
| `--record` | Flag | `False` | Capture smooth 35 FPS MP4 video replay |
| `--headless` | Flag | `False` | Run ViZDoom off-screen without opening a desktop window |
| `--no-display` | Flag | `False` | Disable the Rich live terminal HUD |

---

## Project Structure

```
├── backends/
│   ├── jev_backend.py       # TypeSafe Jev System One integration
│   ├── gemini_backend.py    # Google GenAI Gemini Flash integration
│   └── random_backend.py    # Offline baseline agent (no API key needed)
├── config.py                # Game settings, scenarios, and key constants
├── display.py               # Rich terminal dashboard and summary tables
├── game_loop.py             # Core game loop, frame skipping, and video recorder
├── main.py                  # CLI entry point
├── recordings/              # Saved MP4 gameplay replays (.gitkeep)
├── requirements.txt         # Python package dependencies
├── state_translator.py      # Translates raw ViZDoom game state into JSON
└── .gitignore               # Git ignore rules for venv, pycache, etc.
```
