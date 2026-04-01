"""Test suite for ballistic physics calculations."""

import pytest
import math
from simulator.ballistics import Ballistics, MissileType


class TestBallistics:
    """Test ballistic calculations."""
    
    def test_great_circle_distance(self):
        """Test great circle distance calculation."""
        # New York to Los Angeles (~3944 km)
        distance = Ballistics.great_circle_distance(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < distance < 4000, f"Expected ~3944 km, got {distance}"
        
        # London to Paris (~344 km)
        distance = Ballistics.great_circle_distance(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330 < distance < 360, f"Expected ~344 km, got {distance}"
        
        # Same point = 0 distance
        distance = Ballistics.great_circle_distance(0, 0, 0, 0)
        assert distance == 0, f"Expected 0 km for same point, got {distance}"
        
        # Antipodes (opposite sides of Earth) ~20000 km
        distance = Ballistics.great_circle_distance(0, 0, 0, 180)
        assert 19900 < distance < 20100, f"Expected ~20000 km, got {distance}"
    
    def test_initial_bearing(self):
        """Test initial bearing calculation."""
        # North
        bearing = Ballistics.initial_bearing(0, 0, 90, 0)
        assert 0 <= bearing <= 1, f"Expected ~0° (north), got {bearing}"
        
        # East
        bearing = Ballistics.initial_bearing(0, 0, 0, 90)
        assert 89 <= bearing <= 91, f"Expected ~90° (east), got {bearing}"
        
        # South
        bearing = Ballistics.initial_bearing(0, 0, -90, 0)
        assert 179 <= bearing <= 181, f"Expected ~180° (south), got {bearing}"
    
    def test_intermediate_point(self):
        """Test intermediate point calculation."""
        # Start point
        point = Ballistics.intermediate_point(0, 0, 0, 90, 0.0)
        assert abs(point["lat"]) < 0.01, f"Expected lat ~0, got {point['lat']}"
        assert abs(point["lon"]) < 0.01, f"Expected lon ~0, got {point['lon']}"
        
        # End point
        point = Ballistics.intermediate_point(0, 0, 0, 90, 1.0)
        assert abs(point["lat"]) < 0.01, f"Expected lat ~0, got {point['lat']}"
        assert abs(point["lon"] - 90) < 1, f"Expected lon ~90, got {point['lon']}"
        
        # Midpoint
        point = Ballistics.intermediate_point(0, 0, 0, 180, 0.5)
        assert abs(point["lat"]) < 0.01, f"Expected lat ~0 at equator midpoint, got {point['lat']}"
    
    def test_altitude_at_fraction(self):
        """Test altitude calculation."""
        # Start and end = 0 altitude
        alt = Ballistics.altitude_at_fraction(0.0, 1200, 10000)
        assert alt < 100, f"Expected near 0 at start, got {alt}"
        
        alt = Ballistics.altitude_at_fraction(1.0, 1200, 10000)
        assert alt < 100, f"Expected near 0 at end, got {alt}"
        
        # Midcourse = peak altitude
        alt = Ballistics.altitude_at_fraction(0.5, 1200, 10000)
        assert 800 < alt < 1200, f"Expected near peak at midcourse, got {alt}"
    
    def test_calculate_flight_time(self):
        """Test flight time calculation."""
        # Short distance
        time = Ballistics.calculate_flight_time(1000, "ICBM")
        assert 200 < time < 600, f"Expected 200-600s for 1000km, got {time}"
        
        # Long distance
        time = Ballistics.calculate_flight_time(10000, "ICBM")
        assert 800 < time < 2000, f"Expected 800-2000s for 10000km, got {time}"
        
        # Different missile types
        icbm_time = Ballistics.calculate_flight_time(5000, "ICBM")
        srbm_time = Ballistics.calculate_flight_time(500, "SRBM")
        assert srbm_time < icbm_time, "SRBM should be faster than ICBM for same distance"
    
    def test_velocity_at_fraction(self):
        """Test velocity calculation."""
        # Boost phase - accelerating
        v_boost = Ballistics.velocity_at_fraction(0.05, "ICBM")
        v_mid = Ballistics.velocity_at_fraction(0.5, "ICBM")
        
        # Midcourse should be fastest
        assert v_boost < v_mid, "Midcourse velocity should be higher than boost"
        
        # Terminal phase
        v_term = Ballistics.velocity_at_fraction(0.95, "ICBM")
        assert v_term > 5000, f"Terminal velocity should be high, got {v_term}"
    
    def test_position_at_time(self):
        """Test position calculation."""
        # At start
        pos = Ballistics.position_at_time(0, 0, 0, 90, 0, 3600, "ICBM")
        assert abs(pos["lat"]) < 1, f"Start lat should be ~0, got {pos['lat']}"
        assert abs(pos["lon"]) < 1, f"Start lon should be ~0, got {pos['lon']}"
        assert pos["phase"] == "boost", f"Start phase should be boost, got {pos['phase']}"
        
        # At midcourse
        pos = Ballistics.position_at_time(0, 0, 0, 90, 1800, 3600, "ICBM")
        assert pos["phase"] == "midcourse", f"Midcourse phase, got {pos['phase']}"
        
        # At end
        pos = Ballistics.position_at_time(0, 0, 0, 90, 3600, 3600, "ICBM")
        assert pos["fraction"] >= 0.99, f"End fraction should be ~1, got {pos['fraction']}"
    
    def test_intercept_probability(self):
        """Test intercept probability calculation."""
        # Best chance in midcourse
        p_mid = Ballistics.intercept_probability("midcourse", "GBI", 5000)
        p_boost = Ballistics.intercept_probability("boost", "GBI", 5000)
        p_term = Ballistics.intercept_probability("terminal", "GBI", 5000)
        
        assert p_mid > p_boost, "Midcourse should be better than boost"
        assert p_mid > p_term, "Midcourse should be better than terminal"
        
        # Distance affects THAAD/Patriot
        p_short = Ballistics.intercept_probability("midcourse", "THAAD", 100)
        p_long = Ballistics.intercept_probability("midcourse", "THAAD", 500)
        assert p_short > p_long, "Shorter distance should be better for THAAD"


class TestMissileType:
    """Test missile type configurations."""
    
    def test_missile_type_creation(self):
        """Test missile type dataclass."""
        icbm = Ballistics.MISSILE_TYPES["ICBM"]
        assert icbm.boost_time == 180.0
        assert icbm.max_altitude_km == 1200.0
        assert "Minuteman III" in icbm.types
    
    def test_missile_types_exist(self):
        """Test all missile types are defined."""
        assert "ICBM" in Ballistics.MISSILE_TYPES
        assert "IRBM" in Ballistics.MISSILE_TYPES
        assert "SRBM" in Ballistics.MISSILE_TYPES
    
    def test_get_missile_data(self):
        """Test missile data retrieval."""
        data = Ballistics.get_missile_data("ICBM")
        assert data.max_altitude_km == 1200.0
        
        # Unknown type returns ICBM default
        data = Ballistics.get_missile_data("UNKNOWN")
        assert data.boost_time == 180.0


class TestPhysicsConsistency:
    """Test physics consistency and edge cases."""
    
    def test_distance_symmetry(self):
        """Distance should be symmetric."""
        d1 = Ballistics.great_circle_distance(40, -74, 34, -118)
        d2 = Ballistics.great_circle_distance(34, -118, 40, -74)
        assert abs(d1 - d2) < 0.1, "Distance should be symmetric"
    
    def test_intermediate_point_fraction(self):
        """Test all fractions produce valid points."""
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            point = Ballistics.intermediate_point(0, 0, 45, 90, frac)
            assert -90 <= point["lat"] <= 90, f"Invalid lat at fraction {frac}"
            assert -180 <= point["lon"] <= 180, f"Invalid lon at fraction {frac}"
    
    def test_velocity_bounds(self):
        """Velocity should be reasonable."""
        for frac in [0.01, 0.1, 0.5, 0.9, 0.99]:
            v = Ballistics.velocity_at_fraction(frac, "ICBM")
            assert 0 < v < 15000, f"Velocity {v} out of bounds at fraction {frac}"
    
    def test_intercept_probability_bounds(self):
        """Probability should be between 0.1 and 0.9."""
        for phase in ["boost", "midcourse", "terminal"]:
            for itype in ["GBI", "THAAD", "Patriot"]:
                p = Ballistics.intercept_probability(phase, itype, 1000)
                assert 0.1 <= p <= 0.9, f"Probability {p} out of bounds for {phase}/{itype}"