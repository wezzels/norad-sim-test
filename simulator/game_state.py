"""Game State Manager.

Mirrors the GDScript GameState autoload from norad-war-simulator.
Handles simulation state, missiles, interceptors, and statistics.
"""

import time
import random
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
from pathlib import Path

from .ballistics import Ballistics


class DEFCON(Enum):
    """DEFCON readiness levels."""
    NORMAL = 5
    INCREASED = 4
    AIR_FORCE_READY = 3
    ARMED_FORCES_READY = 2
    MAXIMUM = 1


@dataclass
class Missile:
    """Represents an active missile threat."""
    id: str
    origin: str
    target: str
    missile_type: str
    status: str = "boost"
    altitude: float = 0.0
    speed: float = 0.0
    progress: float = 0.0
    flight_time: float = 0.0
    launch_time: float = 0.0
    warhead_yield: int = 100
    distance_km: float = 0.0
    origin_lat: float = 0.0
    origin_lon: float = 0.0
    target_lat: float = 0.0
    target_lon: float = 0.0
    position: Dict = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0, "alt": 0.0})
    intercepted: bool = False


@dataclass
class Interceptor:
    """Represents an active interceptor."""
    id: str
    missile_id: str
    interceptor_type: str
    status: str = "tracking"
    success: bool = False
    progress: float = 0.0
    launch_time: float = 0.0


@dataclass
class Detonation:
    """Represents a nuclear detonation."""
    id: str
    lat: float
    lon: float
    yield_kt: int
    city: str
    time: str
    confirmed: bool = False
    satellites_detected: List[str] = field(default_factory=list)


class GameState:
    """
    Global game state manager.
    Handles simulation state, missiles, interceptors, satellites.
    """
    
    def __init__(self):
        # Game state
        self.paused: bool = False
        self.speed_multiplier: float = 1.0
        self.current_defcon: int = 3
        self.simulation_time: float = 0.0
        self.real_time: float = 0.0
        
        # Entities
        self.missiles: List[Missile] = []
        self.interceptors: List[Interceptor] = []
        self.detonations: List[Detonation] = []
        self.satellites: List[Dict] = []
        self.alerts: List[str] = []
        
        # Statistics
        self.stats: Dict = {
            "missiles_launched": 0,
            "missiles_intercepted": 0,
            "detonations_detected": 0,
            "cities_hit": 0,
            "threats_active": 0
        }
        
        # Scenario
        self.current_scenario: Dict = {}
        self.scenario_loaded: bool = False
        
        # Data caches
        self._cities: List[Dict] = []
        self._launch_sites: List[Dict] = []
        
        # Callbacks
        self._on_missile_launched: Optional[Callable] = None
        self._on_missile_intercepted: Optional[Callable] = None
        self._on_detonation: Optional[Callable] = None
        self._on_defcon_change: Optional[Callable] = None
        self._on_alert: Optional[Callable] = None
        
        # Load satellite data
        self._load_satellites()
    
    def _load_satellites(self) -> None:
        """Load satellite data from JSON."""
        # Default satellite constellation (GPS-III, DSP, SBIRS)
        self.satellites = [
            {"name": "DSP-1", "type": "DSP", "coverage": "pacific", "lat": 0.0, "lon": 180.0},
            {"name": "DSP-2", "type": "DSP", "coverage": "atlantic", "lat": 0.0, "lon": 0.0},
            {"name": "SBIRS-GEO-1", "type": "SBIRS", "coverage": "global", "lat": 0.0, "lon": 0.0},
            {"name": "GPS-III-1", "type": "GPS", "coverage": "global", "lat": 55.0, "lon": 0.0},
        ]
    
    def load_data(self, data_dir: str = "data") -> None:
        """Load city and launch site data."""
        data_path = Path(data_dir)
        
        # Load cities
        cities_file = data_path / "cities.json"
        if cities_file.exists():
            with open(cities_file) as f:
                self._cities = json.load(f)
        
        # Load launch sites
        sites_file = data_path / "launch_sites.json"
        if sites_file.exists():
            with open(sites_file) as f:
                self._launch_sites = json.load(f)
    
    def get_city_coords(self, city_name: str) -> Dict[str, float]:
        """Get coordinates for a city."""
        for city in self._cities:
            if city.get("name") == city_name:
                return {"lat": city.get("lat", 0.0), "lon": city.get("lon", 0.0)}
        return {"lat": 0.0, "lon": 0.0}
    
    def get_launch_site_coords(self, site_name: str) -> Dict[str, float]:
        """Get coordinates for a launch site."""
        for site in self._launch_sites:
            if site.get("name") == site_name:
                return {"lat": site.get("lat", 0.0), "lon": site.get("lon", 0.0)}
        return {"lat": 0.0, "lon": 0.0}
    
    def reset_state(self) -> None:
        """Reset game state for new scenario."""
        self.missiles.clear()
        self.interceptors.clear()
        self.detonations.clear()
        self.alerts.clear()
        self.simulation_time = 0.0
        self.current_defcon = 3
        self.speed_multiplier = 1.0
        
        self.stats = {
            "missiles_launched": 0,
            "missiles_intercepted": 0,
            "detonations_detected": 0,
            "cities_hit": 0,
            "threats_active": 0
        }
    
    def pause(self) -> None:
        """Pause the simulation."""
        self.paused = True
    
    def resume(self) -> None:
        """Resume the simulation."""
        self.paused = False
    
    def set_speed(self, multiplier: float) -> None:
        """Set simulation speed multiplier."""
        self.speed_multiplier = max(0.1, min(100.0, multiplier))
    
    def set_defcon(self, level: int) -> None:
        """Set DEFCON level (1-5)."""
        level = max(1, min(5, level))
        if level != self.current_defcon:
            old_level = self.current_defcon
            self.current_defcon = level
            
            # Generate alert
            alerts = {
                1: "DEFCON 1 - MAXIMUM READINESS - Nuclear war imminent",
                2: "DEFCON 2 - ARMED FORCES READY - Next step nuclear war",
                3: "DEFCON 3 - AIR FORCE READY - Increase in force readiness",
                4: "DEFCON 4 - INCREASED INTELLIGENCE - Above normal readiness",
                5: "DEFCON 5 - NORMAL READINESS - Lowest state"
            }
            
            self.alerts.append(alerts[level])
            
            if self._on_defcon_change:
                self._on_defcon_change(level)
            
            if self._on_alert:
                self._on_alert({"level": level, "text": alerts[level]})
    
    def launch_missile(self, origin: str, target: str, missile_type: str = "ICBM") -> Missile:
        """
        Launch a new missile threat.
        
        Args:
            origin: Launch site name
            target: Target city name
            missile_type: Type of missile (ICBM, IRBM, SRBM)
            
        Returns:
            The created Missile object
        """
        # Get coordinates
        origin_coords = self.get_launch_site_coords(origin)
        target_coords = self.get_city_coords(target)
        
        # Calculate distance
        distance_km = Ballistics.great_circle_distance(
            origin_coords["lat"], origin_coords["lon"],
            target_coords["lat"], target_coords["lon"]
        )
        
        # Calculate flight time
        flight_time = Ballistics.calculate_flight_time(distance_km, missile_type)
        
        # Create missile
        missile = Missile(
            id=f"THREAT-{time.strftime('%H%M%S')}-{random.randint(100, 999)}",
            origin=origin,
            target=target,
            missile_type=missile_type,
            status="boost",
            flight_time=flight_time,
            launch_time=self.simulation_time,
            warhead_yield=random.randint(100, 800),
            distance_km=distance_km,
            origin_lat=origin_coords["lat"],
            origin_lon=origin_coords["lon"],
            target_lat=target_coords["lat"],
            target_lon=target_coords["lon"]
        )
        
        self.missiles.append(missile)
        self.stats["missiles_launched"] += 1
        self.stats["threats_active"] += 1
        
        if self._on_missile_launched:
            self._on_missile_launched(missile)
        
        return missile
    
    def launch_interceptor(self, missile_id: str, interceptor_type: str = "GBI") -> Interceptor:
        """
        Launch an interceptor at a missile.
        
        Args:
            missile_id: ID of target missile
            interceptor_type: Type (GBI, THAAD, Patriot)
            
        Returns:
            The created Interceptor object, or None if missile not found
        """
        # Find missile
        missile = self.get_missile_by_id(missile_id)
        if not missile:
            return None
        
        # Calculate success based on phase
        success_chance = Ballistics.intercept_probability(
            missile.status, interceptor_type, missile.distance_km
        )
        
        interceptor = Interceptor(
            id=f"INT-{time.strftime('%H%M%S')}-{random.randint(100, 999)}",
            missile_id=missile_id,
            interceptor_type=interceptor_type,
            success=random.random() < success_chance,
            launch_time=self.simulation_time
        )
        
        self.interceptors.append(interceptor)
        return interceptor
    
    def get_missile_by_id(self, missile_id: str) -> Optional[Missile]:
        """Find missile by ID."""
        for missile in self.missiles:
            if missile.id == missile_id:
                return missile
        return None
    
    def update_missiles(self, delta: float) -> None:
        """Update all missile positions."""
        to_remove = []
        
        for missile in self.missiles:
            if missile.intercepted:
                to_remove.append(missile)
                continue
            
            # Update position using ballistics
            elapsed = self.simulation_time - missile.launch_time
            pos = Ballistics.position_at_time(
                missile.origin_lat, missile.origin_lon,
                missile.target_lat, missile.target_lon,
                elapsed, missile.flight_time, missile.missile_type
            )
            
            missile.progress = pos["fraction"] * 100.0
            missile.status = pos["phase"]
            missile.altitude = pos["altitude_km"]
            missile.speed = pos["velocity_ms"]
            missile.position = {
                "lat": pos["lat"],
                "lon": pos["lon"],
                "alt": pos["altitude_km"]
            }
            
            # Check for impact
            if pos["fraction"] >= 1.0:
                self._create_detonation(missile)
                to_remove.append(missile)
                self.stats["cities_hit"] += 1
                self.stats["threats_active"] -= 1
        
        for missile in to_remove:
            if missile in self.missiles:
                self.missiles.remove(missile)
    
    def update_interceptors(self, delta: float) -> None:
        """Update all interceptor positions."""
        to_remove = []
        
        for interceptor in self.interceptors:
            interceptor.progress += delta * 15.0  # Fast intercept
            
            if interceptor.progress >= 100.0:
                if interceptor.success:
                    # Mark target missile as intercepted
                    missile = self.get_missile_by_id(interceptor.missile_id)
                    if missile:
                        missile.intercepted = True
                        self.stats["missiles_intercepted"] += 1
                        self.stats["threats_active"] -= 1
                        
                        if self._on_missile_intercepted:
                            self._on_missile_intercepted(interceptor.missile_id)
                
                to_remove.append(interceptor)
        
        for interceptor in to_remove:
            if interceptor in self.interceptors:
                self.interceptors.remove(interceptor)
    
    def _create_detonation(self, missile: Missile) -> None:
        """Create a detonation event."""
        detonation = Detonation(
            id=f"DET-{time.strftime('%H%M%S')}",
            lat=missile.position["lat"],
            lon=missile.position["lon"],
            yield_kt=missile.warhead_yield,
            city=missile.target,
            time=time.strftime("%H:%M:%S")
        )
        
        self.detonations.append(detonation)
        self.stats["detonations_detected"] += 1
        
        if self._on_detonation:
            self._on_detonation(detonation)
    
    def update(self, delta: float) -> None:
        """
        Update simulation state.
        
        Args:
            delta: Time delta in seconds (real time)
        """
        if self.paused:
            return
        
        # Scale by simulation speed
        sim_delta = delta * self.speed_multiplier
        self.simulation_time += sim_delta
        self.real_time += delta
        
        # Update entities
        self.update_missiles(sim_delta)
        self.update_interceptors(sim_delta)
    
    def get_state(self) -> Dict:
        """Get current game state for serialization/sync."""
        return {
            "paused": self.paused,
            "speed": self.speed_multiplier,
            "defcon": self.current_defcon,
            "simulation_time": self.simulation_time,
            "missiles": [
                {
                    "id": m.id,
                    "origin": m.origin,
                    "target": m.target,
                    "status": m.status,
                    "progress": m.progress,
                    "intercepted": m.intercepted
                }
                for m in self.missiles
            ],
            "interceptors": [
                {
                    "id": i.id,
                    "missile_id": i.missile_id,
                    "type": i.interceptor_type,
                    "progress": i.progress
                }
                for i in self.interceptors
            ],
            "stats": self.stats
        }