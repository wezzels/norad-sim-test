# NORAD War Simulator - Human Emulation Test Suite

A Python-based simulation that plays NORAD War Simulator like a human would, with comprehensive test coverage and video recording.

## Overview

This project creates an AI player that emulates human gameplay patterns for the NORAD War Simulator, then validates every component through automated testing. Includes video recording capability to capture test sessions.

## Architecture

```
norad-sim-test/
├── simulator/
│   ├── __init__.py
│   ├── game_state.py      # Core game state (mirrors GDScript GameState)
│   ├── ballistics.py      # Ballistic physics calculations
│   ├── defense.py         # Defense management (GBI, THAAD, Patriot)
│   ├── detection.py       # Satellite detection simulation
│   ├── scenarios.py       # Scenario loader and wave management
│   ├── human_player.py    # Human-like AI player
│   └── video_recorder.py  # Video recording for test sessions
├── tests/
│   ├── __init__.py
│   ├── test_ballistics.py
│   ├── test_game_state.py
│   ├── test_defense.py
│   ├── test_detection.py
│   ├── test_scenarios.py
│   ├── test_human_player.py
│   ├── test_integration.py
│   └── test_video_recorder.py
├── data/
│   ├── cities.json        # City data (mirrors game data)
│   ├── launch_sites.json  # Launch site data
│   └── scenarios/         # Scenario definitions
├── recordings/            # Output directory for video recordings
├── main.py                # Run simulation
├── run_tests.py           # Run all tests
└── requirements.txt
```

## Installation

```bash
pip install -r requirements.txt
python run_tests.py
```

## Running Simulation

```bash
# Basic run
python main.py --scenario tutorial --verbose

# Run with video recording
python main.py --scenario cold_war --record --verbose

# Run multiple times
python main.py --scenario mass_attack --runs 10 --record

# List available scenarios
python main.py --list-scenarios
```

## Video Recording

Record simulation sessions to MP4, GIF, or WebM format:

```python
from simulator import GameState, DefenseManager, DetectionManager, ScenarioLoader, HumanPlayer
from simulator.video_recorder import VideoRecorder, RecordingConfig

# Configure recording
config = RecordingConfig(
    output_dir="recordings",
    format="mp4",           # mp4, gif, or webm
    fps=30,
    resolution=(1920, 1080),  # Full HD
    show_grid=True,
    show_trajectories=True,
    show_defcon=True,
    show_stats=True
)

# Create recorder
recorder = VideoRecorder(config)
recorder.start_recording("my_scenario")

# Run simulation and capture frames
for frame in simulation:
    recorder.capture_frame(game_state, events)

# Generate video
video_path = recorder.stop_recording()
```

### Recording Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_dir` | str | "recordings" | Directory for video files |
| `format` | str | "mp4" | Output format (mp4, gif, webm) |
| `fps` | int | 30 | Frames per second |
| `resolution` | tuple | (1280, 720) | Video resolution (width, height) |
| `show_grid` | bool | True | Show lat/lon grid |
| `show_trajectories` | bool | True | Show missile flight paths |
| `show_defcon` | bool | True | Show DEFCON level |
| `show_stats` | bool | True | Show statistics overlay |
| `compression` | str | "medium" | Compression level (low, medium, high) |

## Test Coverage

- **Ballistics**: Great circle distance, flight time, trajectory calculations
- **Game State**: Missile tracking, interceptor management, DEFCON levels
- **Defense**: Interceptor types, success probabilities, inventory
- **Detection**: Satellite coverage, threat detection timing
- **Scenarios**: Wave spawning, timing, completion conditions
- **Human Player**: Reaction time, decision patterns, risk tolerance
- **Video Recorder**: Frame capture, encoding, visual elements

## Human Emulation Features

- Variable reaction times (0.3-2.0 seconds)
- Learning curve (improves with practice)
- Stress response (faster decisions under threat)
- Mistake modeling (occasional mis-clicks)
- Priority assessment (cities vs interceptors)
- Resource management (save interceptors for critical threats)

## Test Results

```
22 video recorder tests passing
103 total tests passing
```

## Dependencies

- Python 3.8+
- pytest (testing)
- matplotlib (video generation)
- numpy (calculations)
- ffmpeg (video encoding, system package)

## License

MIT License