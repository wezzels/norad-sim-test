"""Detection Manager.

Simulates satellite-based threat detection.
Mirrors the GDScript DetectionManager from norad-war-simulator.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time

from .game_state import Missile


@dataclass
class Satellite:
    """Represents a detection satellite."""
    name: str
    satellite_type: str  # DSP, SBIRS, GPS-III
    coverage: str
    lat: float
    lon: float
    detection_range_km: float = 20000.0
    refresh_rate: float = 2.0  # seconds
    last_scan: float = 0.0


class DetectionManager:
    """
    Manages satellite-based threat detection.
    
    Simulates the DSP (Defense Support Program) and SBIRS 
    (Space-Based Infrared System) satellite networks.
    """
    
    # Satellite configurations
    SATELLITE_CONFIGS = {
        "DSP": {
            "detection_range": 20000,  # km
            "refresh_rate": 2.0,  # seconds
            "accuracy": 0.85  # detection probability
        },
        "SBIRS": {
            "detection_range": 25000,
            "refresh_rate": 1.0,
            "accuracy": 0.95
        },
        "GPS-III": {
            "detection_range": 15000,
            "refresh_rate": 5.0,
            "accuracy": 0.70
        }
    }
    
    def __init__(self):
        self.satellites: List[Satellite] = []
        self.detected_missiles: Dict[str, float] = {}  # missile_id -> detection_time
        self.detection_log: List[Dict] = []
        
        self._initialize_satellites()
    
    def _initialize_satellites(self) -> None:
        """Initialize satellite constellation."""
        # DSP satellites (geostationary)
        self.satellites = [
            Satellite("DSP-1", "DSP", "pacific", 0.0, 180.0),
            Satellite("DSP-2", "DSP", "atlantic", 0.0, 0.0),
            Satellite("DSP-3", "DSP", "indian", 0.0, 75.0),
            Satellite("DSP-4", "DSP", "european", 0.0, -15.0),
        ]
        
        # SBIRS satellites (highly elliptical + geostationary)
        self.satellites.extend([
            Satellite("SBIRS-GEO-1", "SBIRS", "global", 0.0, 0.0),
            Satellite("SBIRS-GEO-2", "SBIRS", "global", 0.0, 90.0),
            Satellite("SBIRS-HEO-1", "SBIRS", "arctic", 63.0, 0.0),
        ])
        
        # GPS-III (navigation, limited detection)
        for i in range(6):
            lon = i * 60.0
            self.satellites.append(
                Satellite(f"GPS-III-{i+1}", "GPS-III", "global", 55.0, lon)
            )
    
    def can_detect(self, satellite: Satellite, missile: Missile, current_time: float) -> bool:
        """
        Check if a satellite can detect a missile.
        
        Args:
            satellite: The detecting satellite
            missile: The target missile
            current_time: Current simulation time
            
        Returns:
            True if satellite can detect the missile
        """
        # Check if satellite has refreshed
        if current_time - satellite.last_scan < satellite.refresh_rate:
            return False
        
        # Get config
        config = self.SATELLITE_CONFIGS.get(satellite.satellite_type, {})
        
        # Calculate distance to missile
        from .ballistics import Ballistics
        distance = Ballistics.great_circle_distance(
            satellite.lat, satellite.lon,
            missile.position.get("lat", 0), missile.position.get("lon", 0)
        )
        
        # Check range
        if distance > config.get("detection_range", 20000):
            return False
        
        # Check detection probability
        accuracy = config.get("accuracy", 0.85)
        
        # Boost phase is easiest to detect (heat signature)
        if missile.status == "boost":
            accuracy *= 1.2
        elif missile.status == "terminal":
            accuracy *= 0.8
        
        # Random detection
        import random
        return random.random() < accuracy
    
    def detect_missiles(self, missiles: List[Missile], current_time: float) -> List[Dict]:
        """
        Scan for missile threats.
        
        Args:
            missiles: All active missiles
            current_time: Current simulation time
            
        Returns:
            List of newly detected missiles
        """
        newly_detected = []
        
        for satellite in self.satellites:
            for missile in missiles:
                # Skip if already detected
                if missile.id in self.detected_missiles:
                    continue
                
                # Skip if intercepted
                if missile.intercepted:
                    continue
                
                # Try to detect
                if self.can_detect(satellite, missile, current_time):
                    # Mark as detected
                    self.detected_missiles[missile.id] = current_time
                    
                    # Log detection
                    detection = {
                        "missile_id": missile.id,
                        "satellite": satellite.name,
                        "type": satellite.satellite_type,
                        "time": current_time,
                        "lat": missile.position.get("lat", 0),
                        "lon": missile.position.get("lon", 0),
                        "phase": missile.status
                    }
                    self.detection_log.append(detection)
                    newly_detected.append(detection)
        
        return newly_detected
    
    def get_time_since_detection(self, missile_id: str, current_time: float) -> Optional[float]:
        """Get time elapsed since missile was detected."""
        if missile_id in self.detected_missiles:
            return current_time - self.detected_missiles[missile_id]
        return None
    
    def get_satellite_coverage(self, lat: float, lon: float) -> List[str]:
        """
        Get list of satellites that can see a location.
        
        Args:
            lat, lon: Location to check
            
        Returns:
            List of satellite names with coverage
        """
        from .ballistics import Ballistics
        
        covering = []
        for satellite in self.satellites:
            distance = Ballistics.great_circle_distance(
                satellite.lat, satellite.lon, lat, lon
            )
            config = self.SATELLITE_CONFIGS.get(satellite.satellite_type, {})
            max_range = config.get("detection_range", 20000)
            
            if distance <= max_range:
                covering.append(satellite.name)
        
        return covering
    
    def get_detection_stats(self) -> Dict:
        """Get detection statistics."""
        return {
            "satellites": len(self.satellites),
            "detected_missiles": len(self.detected_missiles),
            "detections": len(self.detection_log),
            "satellite_types": {
                stype: sum(1 for s in self.satellites if s.satellite_type == stype)
                for stype in ["DSP", "SBIRS", "GPS-III"]
            }
        }