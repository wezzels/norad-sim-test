"""Ballistic missile physics calculations.

Mirrors the GDScript Ballistics class from norad-war-simulator.
Uses real physics for ICBM trajectory calculations.
"""

import math
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class MissileType:
    """Configuration for a missile type."""
    boost_time: float  # seconds
    boost_acceleration: float  # m/s²
    burnout_velocity: float  # m/s
    max_altitude_km: float
    reentry_velocity: float  # m/s
    warhead_mass_kg: float
    types: list
    
    @classmethod
    def from_dict(cls, data: dict) -> "MissileType":
        return cls(
            boost_time=data.get("boost_time", 180.0),
            boost_acceleration=data.get("boost_acceleration", 30.0),
            burnout_velocity=data.get("burnout_velocity", 7000.0),
            max_altitude_km=data.get("max_altitude_km", 1200.0),
            reentry_velocity=data.get("reentry_velocity", 7000.0),
            warhead_mass_kg=data.get("warhead_mass_kg", 500.0),
            types=data.get("types", ["Unknown"])
        )


class Ballistics:
    """
    Accurate ballistic missile trajectory calculations.
    Based on real ICBM physics with Earth curvature.
    """
    
    # Physical constants
    EARTH_RADIUS_KM = 6371.0
    GRAVITY = 9.81  # m/s²
    EARTH_MASS = 5.972e24  # kg
    GRAVITATIONAL_CONSTANT = 6.674e-11  # m³/(kg·s²)
    
    # Missile type configurations
    MISSILE_TYPES = {
        "ICBM": MissileType.from_dict({
            "boost_time": 180.0,
            "boost_acceleration": 30.0,
            "burnout_velocity": 7000.0,
            "max_altitude_km": 1200.0,
            "reentry_velocity": 7000.0,
            "warhead_mass_kg": 500.0,
            "types": ["Minuteman III", "Peacekeeper", "SS-18", "DF-41"]
        }),
        "IRBM": MissileType.from_dict({
            "boost_time": 120.0,
            "boost_acceleration": 25.0,
            "burnout_velocity": 4000.0,
            "max_altitude_km": 600.0,
            "reentry_velocity": 4000.0,
            "warhead_mass_kg": 750.0,
            "types": ["Taepodong-2", "Agni-V", "Shahab-3"]
        }),
        "SRBM": MissileType.from_dict({
            "boost_time": 60.0,
            "boost_acceleration": 20.0,
            "burnout_velocity": 2000.0,
            "max_altitude_km": 150.0,
            "reentry_velocity": 2000.0,
            "warhead_mass_kg": 1000.0,
            "types": ["Scud", "Iskander", "ATACMS"]
        })
    }
    
    @classmethod
    def great_circle_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance in km using Haversine formula.
        
        Args:
            lat1, lon1: Origin coordinates in degrees
            lat2, lon2: Target coordinates in degrees
            
        Returns:
            Distance in kilometers
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon1_rad = math.radians(lon1)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return cls.EARTH_RADIUS_KM * c
    
    @classmethod
    def initial_bearing(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate initial bearing from point 1 to point 2.
        
        Returns:
            Bearing in degrees (0-360)
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        x = math.cos(lat2_rad) * math.sin(dlon_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360.0) % 360.0
    
    @classmethod
    def intermediate_point(cls, lat1: float, lon1: float, lat2: float, lon2: float, 
                          fraction: float) -> Dict[str, float]:
        """
        Get lat/lon at fraction (0-1) along great circle path.
        
        Args:
            lat1, lon1: Origin coordinates
            lat2, lon2: Target coordinates
            fraction: Position along path (0.0 = origin, 1.0 = target)
            
        Returns:
            Dict with 'lat' and 'lon' keys
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon1_rad = math.radians(lon1)
        lon2_rad = math.radians(lon2)
        
        d = cls.great_circle_distance(lat1, lon1, lat2, lon2) / cls.EARTH_RADIUS_KM
        
        if d == 0:
            return {"lat": lat1, "lon": lon1}
        
        a = math.sin((1 - fraction) * d) / math.sin(d)
        b = math.sin(fraction * d) / math.sin(d)
        
        x = a * math.cos(lat1_rad) * math.cos(lon1_rad) + b * math.cos(lat2_rad) * math.cos(lon2_rad)
        y = a * math.cos(lat1_rad) * math.sin(lon1_rad) + b * math.cos(lat2_rad) * math.sin(lon2_rad)
        z = a * math.sin(lat1_rad) + b * math.sin(lat2_rad)
        
        lat = math.degrees(math.atan2(z, math.sqrt(x*x + y*y)))
        lon = math.degrees(math.atan2(y, x))
        
        return {"lat": lat, "lon": lon}
    
    @classmethod
    def altitude_at_fraction(cls, fraction: float, max_altitude: float, 
                             total_distance: float) -> float:
        """
        Calculate altitude at fraction of trajectory.
        
        Uses asymmetric profile: boost (15%), midcourse (70%), terminal (15%)
        """
        if fraction < 0.15:
            # Boost phase - rapid altitude increase
            return max_altitude * (fraction / 0.15) ** 0.8 * 0.3
        elif fraction < 0.50:
            # Midcourse climbing to apogee
            t = (fraction - 0.15) / 0.35
            return max_altitude * (0.3 + 0.7 * math.sin(math.pi * t / 2))
        elif fraction < 0.85:
            # Midcourse descending
            t = (fraction - 0.50) / 0.35
            return max_altitude * (1.0 - 0.3 * t)
        else:
            # Terminal phase - rapid descent
            t = (fraction - 0.85) / 0.15
            return max_altitude * 0.7 * (1.0 - t) ** 1.5
    
    @classmethod
    def calculate_flight_time(cls, distance_km: float, missile_type: str = "ICBM") -> float:
        """
        Calculate total flight time in seconds.
        
        Args:
            distance_km: Distance between launch and target
            missile_type: Type of missile (ICBM, IRBM, SRBM)
            
        Returns:
            Flight time in seconds
        """
        type_data = cls.MISSILE_TYPES.get(missile_type, cls.MISSILE_TYPES["ICBM"])
        boost_time = type_data.boost_time
        
        # Coasting time
        coast_velocity = type_data.burnout_velocity / 1000.0  # km/s
        coast_distance = max(0, distance_km - 100.0)
        coast_time = coast_distance / coast_velocity
        
        # Terminal phase (reentry)
        terminal_time = 120.0
        
        return boost_time + coast_time + terminal_time
    
    @classmethod
    def velocity_at_fraction(cls, fraction: float, missile_type: str = "ICBM") -> float:
        """
        Calculate velocity in m/s at given fraction of trajectory.
        """
        type_data = cls.MISSILE_TYPES.get(missile_type, cls.MISSILE_TYPES["ICBM"])
        
        if fraction < 0.15:
            # Boost phase - accelerating
            t = fraction / 0.15
            return type_data.boost_acceleration * type_data.boost_time * t
        elif fraction < 0.85:
            # Midcourse - roughly constant
            return type_data.burnout_velocity * (0.9 + 0.2 * (0.5 - abs(fraction - 0.5)))
        else:
            # Terminal - accelerating due to gravity
            t = (fraction - 0.85) / 0.15
            return type_data.reentry_velocity * (1.0 + 0.3 * t)
    
    @classmethod
    def position_at_time(cls, origin_lat: float, origin_lon: float, target_lat: float, target_lon: float,
                        elapsed_time: float, total_time: float, missile_type: str = "ICBM") -> Dict:
        """
        Calculate position (lat, lon, altitude) at given time.
        
        Returns:
            Dict with lat, lon, altitude_km, velocity_ms, phase, fraction
        """
        fraction = max(0.0, min(1.0, elapsed_time / total_time))
        
        # Get ground position
        ground_pos = cls.intermediate_point(origin_lat, origin_lon, target_lat, target_lon, fraction)
        
        # Get altitude
        distance = cls.great_circle_distance(origin_lat, origin_lon, target_lat, target_lon)
        type_data = cls.MISSILE_TYPES.get(missile_type, cls.MISSILE_TYPES["ICBM"])
        altitude = cls.altitude_at_fraction(fraction, type_data.max_altitude_km, distance)
        
        # Get velocity
        velocity = cls.velocity_at_fraction(fraction, missile_type)
        
        # Determine phase
        if fraction < 0.15:
            phase = "boost"
        elif fraction >= 0.85:
            phase = "terminal"
        else:
            phase = "midcourse"
        
        return {
            "lat": ground_pos["lat"],
            "lon": ground_pos["lon"],
            "altitude_km": altitude,
            "velocity_ms": velocity,
            "phase": phase,
            "fraction": fraction
        }
    
    @classmethod
    def intercept_probability(cls, missile_phase: str, interceptor_type: str, 
                             distance_km: float = 0) -> float:
        """
        Calculate probability of successful intercept.
        
        Based on real-world performance data.
        """
        # Base probabilities by interceptor type
        base_prob = {
            "GBI": 0.55,
            "THAAD": 0.60,
            "Patriot": 0.45,
            "Aegis": 0.65
        }
        
        prob = base_prob.get(interceptor_type, 0.5)
        
        # Phase modifiers
        phase_mod = {
            "boost": 0.3,
            "midcourse": 1.0,
            "terminal": 0.7
        }
        prob *= phase_mod.get(missile_phase, 0.8)
        
        # Distance modifiers (for THAAD/Patriot)
        if interceptor_type == "THAAD" and distance_km > 150:
            prob *= 0.8
        elif interceptor_type == "Patriot" and distance_km > 50:
            prob *= 0.6
        
        return max(0.1, min(0.9, prob))
    
    @classmethod
    def get_missile_data(cls, missile_type: str) -> MissileType:
        """Get configuration for a missile type."""
        return cls.MISSILE_TYPES.get(missile_type, cls.MISSILE_TYPES["ICBM"])