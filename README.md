# NORAD War Simulator - Human Emulation Test Suite

A Python-based simulation that plays NORAD War Simulator like a human would, with comprehensive test coverage.

## Overview

This project creates an AI player that emulates human gameplay patterns for the NORAD War Simulator, then validates every component through automated testing.

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
│   └── human_player.py    # Human-like AI player
├── tests/
│   ├── __init__.py
│   ├── test_ballistics.py
│   ├── test_game_state.py
│   ├── test_defense.py
│   ├── test_detection.py
│   ├── test_scenarios.py
│   ├── test_human_player.py
│   └── test_integration.py
├── data/
│   ├── cities.json        # City data (mirrors game data)
│   ├── launch_sites.json  # Launch site data
│   └── scenarios/         # Scenario definitions
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
python main.py --scenario tutorial --verbose
python main.py --scenario cold_war --human-mode
```

## Test Coverage

- **Ballistics**: Great circle distance, flight time, trajectory calculations
- **Game State**: Missile tracking, interceptor management, DEFCON levels
- **Defense**: Interceptor types, success probabilities, inventory
- **Detection**: Satellite coverage, threat detection timing
- **Scenarios**: Wave spawning, timing, completion conditions
- **Human Player**: Reaction time, decision patterns, risk tolerance

## Human Emulation Features

- Variable reaction times (0.3-2.0 seconds)
- Learning curve (improves with practice)
- Stress response (faster decisions under threat)
- Mistake modeling (occasional mis-clicks)
- Priority assessment (cities vs interceptors)
- Resource management (save interceptors for critical threats)

## License

MIT License