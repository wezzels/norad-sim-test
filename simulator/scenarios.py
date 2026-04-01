"""Scenario Loader.

Loads and manages game scenarios.
Mirrors the GDScript ScenarioLoader from norad-war-simulator.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from pathlib import Path


@dataclass
class Wave:
    """A wave of missile launches."""
    wave_number: int
    missiles: List[Dict]  # List of missile configs
    delay: float = 0.0  # Delay before wave starts
    interval: float = 5.0  # Time between missiles in wave


@dataclass 
class Scenario:
    """A game scenario."""
    id: str
    name: str
    description: str
    difficulty: int  # 1-5
    waves: List[Wave]
    interceptors: Dict[str, int]  # Type -> count
    time_limit: float = 0.0  # 0 = no limit
    victory_condition: str = "all_intercepted"
    
    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        """Create scenario from dictionary."""
        waves = []
        for i, wave_data in enumerate(data.get("waves", [])):
            waves.append(Wave(
                wave_number=i,
                missiles=wave_data.get("missiles", []),
                delay=wave_data.get("delay", i * 60.0),
                interval=wave_data.get("interval", 5.0)
            ))
        
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            difficulty=data.get("difficulty", 3),
            waves=waves,
            interceptors=data.get("interceptors", {"GBI": 44, "THAAD": 100, "Patriot": 200}),
            time_limit=data.get("time_limit", 0.0),
            victory_condition=data.get("victory_condition", "all_intercepted")
        )


class ScenarioLoader:
    """Loads and manages scenarios."""
    
    # Built-in scenarios
    BUILTIN_SCENARIOS = [
        {
            "id": "tutorial",
            "name": "Tutorial: First Contact",
            "description": "Learn the basics of missile defense. A single missile approaches.",
            "difficulty": 1,
            "waves": [
                {
                    "missiles": [
                        {"origin": "Test Site Alpha", "target": "Los Angeles", "type": "SRBM"}
                    ],
                    "delay": 10.0,
                    "interval": 0
                }
            ],
            "interceptors": {"GBI": 44, "THAAD": 100, "Patriot": 200}
        },
        {
            "id": "cold_war",
            "name": "Cold War Crisis",
            "description": "A small-scale exchange. 10 missiles from various origins.",
            "difficulty": 2,
            "waves": [
                {
                    "missiles": [
                        {"origin": "Site A", "target": "New York", "type": "ICBM"},
                        {"origin": "Site B", "target": "Washington DC", "type": "ICBM"},
                    ],
                    "delay": 30.0,
                    "interval": 10.0
                },
                {
                    "missiles": [
                        {"origin": "Site C", "target": "Los Angeles", "type": "IRBM"},
                        {"origin": "Site D", "target": "Chicago", "type": "ICBM"},
                    ],
                    "delay": 120.0,
                    "interval": 15.0
                },
                {
                    "missiles": [
                        {"origin": "Site E", "target": "San Francisco", "type": "ICBM"},
                        {"origin": "Site F", "target": "Seattle", "type": "IRBM"},
                    ],
                    "delay": 240.0,
                    "interval": 20.0
                }
            ],
            "interceptors": {"GBI": 30, "THAAD": 60, "Patriot": 150}
        },
        {
            "id": "regional_conflict",
            "name": "Regional Conflict",
            "description": "A regional power launches 25 missiles at allied cities.",
            "difficulty": 3,
            "waves": [
                {
                    "missiles": [
                        {"origin": "Launch Site 1", "target": "Tokyo", "type": "IRBM"},
                        {"origin": "Launch Site 2", "target": "Seoul", "type": "SRBM"},
                        {"origin": "Launch Site 3", "target": "Guam", "type": "IRBM"},
                        {"origin": "Launch Site 4", "target": "Honolulu", "type": "ICBM"},
                        {"origin": "Launch Site 5", "target": "Anchorage", "type": "ICBM"},
                    ],
                    "delay": 0.0,
                    "interval": 30.0
                },
                {
                    "missiles": [
                        {"origin": "Launch Site 1", "target": "San Diego", "type": "ICBM"},
                        {"origin": "Launch Site 2", "target": "Los Angeles", "type": "ICBM"},
                        {"origin": "Launch Site 3", "target": "San Francisco", "type": "ICBM"},
                        {"origin": "Launch Site 4", "target": "Seattle", "type": "ICBM"},
                        {"origin": "Launch Site 5", "target": "Portland", "type": "ICBM"},
                    ],
                    "delay": 180.0,
                    "interval": 20.0
                }
            ],
            "interceptors": {"GBI": 44, "THAAD": 80, "Patriot": 120}
        },
        {
            "id": "major_exchange",
            "name": "Major Exchange",
            "description": "Full-scale nuclear war. 50+ missiles across multiple waves.",
            "difficulty": 4,
            "waves": [
                {
                    "missiles": [
                        {"origin": f"Site {i}", "target": ["New York", "Washington DC", "Los Angeles", "Chicago", "Houston"][i % 5], "type": "ICBM"}
                        for i in range(10)
                    ],
                    "delay": 0.0,
                    "interval": 15.0
                },
                {
                    "missiles": [
                        {"origin": f"Site {i}", "target": ["San Francisco", "Seattle", "Boston", "Philadelphia", "Phoenix"][i % 5], "type": "ICBM"}
                        for i in range(10, 20)
                    ],
                    "delay": 300.0,
                    "interval": 10.0
                },
                {
                    "missiles": [
                        {"origin": f"Site {i}", "target": ["Dallas", "Denver", "Detroit", "Miami", "Atlanta"][i % 5], "type": "IRBM"}
                        for i in range(20, 30)
                    ],
                    "delay": 600.0,
                    "interval": 8.0
                },
                {
                    "missiles": [
                        {"origin": f"Site {i}", "target": ["Minneapolis", "San Diego", "Tampa", "Baltimore", "Orlando"][i % 5], "type": "ICBM"}
                        for i in range(30, 40)
                    ],
                    "delay": 900.0,
                    "interval": 5.0
                },
                {
                    "missiles": [
                        {"origin": f"Site {i}", "target": ["Cleveland", "Pittsburgh", "St. Louis", "Charlotte", "Las Vegas"][i % 5], "type": "SRBM"}
                        for i in range(40, 50)
                    ],
                    "delay": 1200.0,
                    "interval": 3.0
                }
            ],
            "interceptors": {"GBI": 44, "THAAD": 100, "Patriot": 200}
        },
        {
            "id": "apocalypse",
            "name": "Apocalypse",
            "description": "The end of the world. 100+ missiles from all directions.",
            "difficulty": 5,
            "waves": [
                {
                    "missiles": [
                        {"origin": f"Launch Site {i}", "target": f"City {i % 50}", "type": "ICBM" if i % 3 == 0 else "IRBM"}
                        for i in range(25)
                    ],
                    "delay": 0.0,
                    "interval": 5.0
                },
                {
                    "missiles": [
                        {"origin": f"Launch Site {i}", "target": f"City {i % 50}", "type": "ICBM"}
                        for i in range(25, 50)
                    ],
                    "delay": 180.0,
                    "interval": 3.0
                },
                {
                    "missiles": [
                        {"origin": f"Launch Site {i}", "target": f"City {i % 50}", "type": "ICBM" if i % 2 == 0 else "IRBM"}
                        for i in range(50, 75)
                    ],
                    "delay": 360.0,
                    "interval": 2.0
                },
                {
                    "missiles": [
                        {"origin": f"Launch Site {i}", "target": f"City {i % 50}", "type": "ICBM"}
                        for i in range(75, 100)
                    ],
                    "delay": 540.0,
                    "interval": 1.0
                }
            ],
            "interceptors": {"GBI": 44, "THAAD": 100, "Patriot": 200}
        }
    ]
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.scenarios: Dict[str, Scenario] = {}
        self.current_scenario: Optional[Scenario] = None
        self.current_wave: int = 0
        self.wave_start_time: float = 0.0
        self.missiles_spawned_in_wave: int = 0
        self.scenario_complete: bool = False
        
        # Callbacks
        self.on_wave_start: Optional[Callable] = None
        self.on_wave_end: Optional[Callable] = None
        self.on_scenario_complete: Optional[Callable] = None
        
        # Load built-in scenarios
        self._load_builtin_scenarios()
    
    def _load_builtin_scenarios(self) -> None:
        """Load built-in scenarios."""
        for scenario_data in self.BUILTIN_SCENARIOS:
            scenario = Scenario.from_dict(scenario_data)
            self.scenarios[scenario.id] = scenario
    
    def load_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Load a scenario by ID."""
        if scenario_id in self.scenarios:
            self.current_scenario = self.scenarios[scenario_id]
            self.current_wave = 0
            self.wave_start_time = 0.0
            self.missiles_spawned_in_wave = 0
            self.scenario_complete = False
            return self.current_scenario
        return None
    
    def start_scenario(self) -> None:
        """Start the current scenario."""
        if not self.current_scenario:
            return
        
        self.current_wave = 0
        self.wave_start_time = 0.0
        self.scenario_complete = False
        
        if self.current_scenario.waves:
            self.wave_start_time = self.current_scenario.waves[0].delay
            if self.on_wave_start:
                self.on_wave_start(0)
    
    def update(self, simulation_time: float) -> List[Dict]:
        """
        Update scenario and spawn missiles.
        
        Args:
            simulation_time: Current simulation time in seconds
            
        Returns:
            List of missiles to spawn
        """
        if not self.current_scenario or self.scenario_complete:
            return []
        
        missiles_to_spawn = []
        
        # Check current wave
        if self.current_wave >= len(self.current_scenario.waves):
            # All waves complete
            self.scenario_complete = True
            if self.on_scenario_complete:
                self.on_scenario_complete()
            return []
        
        wave = self.current_scenario.waves[self.current_wave]
        
        # Check if wave should start
        if simulation_time < wave.delay:
            return []
        
        # Time within wave
        wave_time = simulation_time - wave.delay
        
        # Spawn missiles based on interval
        expected_missiles = int(wave_time / wave.interval) if wave.interval > 0 else len(wave.missiles)
        
        if expected_missiles > self.missiles_spawned_in_wave:
            # Spawn new missiles
            for i in range(self.missiles_spawned_in_wave, min(expected_missiles, len(wave.missiles))):
                missiles_to_spawn.append(wave.missiles[i])
                self.missiles_spawned_in_wave = i + 1
        
        # Check if wave is complete
        if self.missiles_spawned_in_wave >= len(wave.missiles):
            if self.on_wave_end:
                self.on_wave_end(self.current_wave)
            
            # Move to next wave
            self.current_wave += 1
            self.missiles_spawned_in_wave = 0
            
            if self.current_wave < len(self.current_scenario.waves):
                self.wave_start_time = self.current_scenario.waves[self.current_wave].delay
                if self.on_wave_start:
                    self.on_wave_start(self.current_wave)
        
        return missiles_to_spawn
    
    def is_complete(self) -> bool:
        """Check if scenario is complete."""
        return self.scenario_complete
    
    def get_progress(self) -> Dict:
        """Get scenario progress."""
        if not self.current_scenario:
            return {"progress": 0.0}
        
        total_waves = len(self.current_scenario.waves)
        return {
            "current_wave": self.current_wave,
            "total_waves": total_waves,
            "progress": self.current_wave / max(1, total_waves),
            "missiles_spawned": self.missiles_spawned_in_wave,
            "scenario_id": self.current_scenario.id
        }
    
    def get_available_scenarios(self) -> List[Dict]:
        """Get list of available scenarios."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "difficulty": s.difficulty,
                "waves": len(s.waves)
            }
            for s in self.scenarios.values()
        ]