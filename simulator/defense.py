"""Defense Manager.

Manages interceptor inventory and launch decisions.
Mirrors the GDScript DefenseManager from norad-war-simulator.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

from .game_state import GameState, Missile


@dataclass
class InterceptorType:
    """Configuration for an interceptor type."""
    name: str
    range_km: float
    max_altitude_km: float
    speed_kmps: float
    success_base: float
    total: int
    available: int
    
    @classmethod
    def create(cls, name: str, total: int) -> "InterceptorType":
        """Create an interceptor type with default values."""
        configs = {
            "GBI": {"range": 5000.0, "altitude": 2000.0, "speed": 8.0, "success": 0.55},
            "THAAD": {"range": 200.0, "altitude": 150.0, "speed": 2.8, "success": 0.60},
            "Patriot": {"range": 160.0, "altitude": 24.0, "speed": 1.5, "success": 0.45}
        }
        
        config = configs.get(name, configs["GBI"])
        return cls(
            name=name,
            range_km=config["range"],
            max_altitude_km=config["altitude"],
            speed_kmps=config["speed"],
            success_base=config["success"],
            total=total,
            available=total
        )


class DefenseManager:
    """
    Manages interceptor inventory and defense decisions.
    
    The DefenseManager tracks:
    - Interceptor inventory (GBI, THAAD, Patriot)
    - Defense sites and their coverage
    - Launch success probabilities
    """
    
    # Default inventory
    DEFAULT_INVENTORY = {
        "GBI": {"total": 44, "available": 44},
        "THAAD": {"total": 100, "available": 100},
        "Patriot": {"total": 200, "available": 200}
    }
    
    # Success probability modifiers by phase
    PHASE_MODIFIERS = {
        "boost": 0.3,
        "midcourse": 1.0,
        "terminal": 0.7
    }
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        
        # Interceptor inventory
        self.inventory: Dict[str, InterceptorType] = {}
        self._initialize_inventory()
        
        # Defense sites (major US defense locations)
        self.defense_sites = [
            {"name": "Fort Greely", "lat": 63.8845, "lon": -145.7356, "types": ["GBI"]},
            {"name": "Vandenberg", "lat": 34.7420, "lon": -120.5725, "types": ["GBI"]},
            {"name": "Fort Bliss", "lat": 31.8012, "lon": -106.4171, "types": ["THAAD"]},
            {"name": "Guam", "lat": 13.4443, "lon": 144.7937, "types": ["THAAD", "Patriot"]},
            {"name": "South Korea", "lat": 35.9078, "lon": 127.7669, "types": ["THAAD", "Patriot"]},
        ]
        
        # Pending intercepts (missile_id -> interceptor_type)
        self.pending_launches: Dict[str, str] = {}
    
    def _initialize_inventory(self) -> None:
        """Initialize interceptor inventory."""
        for name, counts in self.DEFAULT_INVENTORY.items():
            self.inventory[name] = InterceptorType.create(name, counts["total"])
    
    def reset_inventory(self, custom_inventory: Optional[Dict] = None) -> None:
        """Reset or customize interceptor inventory."""
        if custom_inventory:
            for name, counts in custom_inventory.items():
                # Handle both dict and int formats
                if isinstance(counts, int):
                    total = counts
                    available = counts
                else:
                    total = counts.get("total", 0)
                    available = counts.get("available", total)
                self.inventory[name] = InterceptorType.create(name, total)
                self.inventory[name].available = available
        else:
            self._initialize_inventory()
    
    def get_available(self, interceptor_type: str) -> int:
        """Get number of available interceptors of a type."""
        if interceptor_type in self.inventory:
            return self.inventory[interceptor_type].available
        return 0
    
    def get_total(self, interceptor_type: str) -> int:
        """Get total number of interceptors of a type."""
        if interceptor_type in self.inventory:
            return self.inventory[interceptor_type].total
        return 0
    
    def can_intercept(self, missile: Missile, interceptor_type: str) -> bool:
        """
        Check if an interceptor can reach a missile.
        
        Args:
            missile: The target missile
            interceptor_type: Type of interceptor (GBI, THAAD, Patriot)
            
        Returns:
            True if interception is possible
        """
        # Check availability
        if self.get_available(interceptor_type) <= 0:
            return False
        
        # Get interceptor config
        interceptor = self.inventory.get(interceptor_type)
        if not interceptor:
            return False
        
        # Check range (need site within range)
        # For simplicity, assume global coverage for GBI, regional for others
        if interceptor_type == "GBI":
            return True  # GBI has global range
        
        # For THAAD/Patriot, check if missile is within regional coverage
        # This is simplified - real implementation would check site proximity
        if interceptor_type in ["THAAD", "Patriot"]:
            # Check if any defense site can reach
            missile_pos = (missile.target_lat, missile.target_lon)
            for site in self.defense_sites:
                if interceptor_type in site["types"]:
                    # Simplified range check
                    from .ballistics import Ballistics
                    dist = Ballistics.great_circle_distance(
                        site["lat"], site["lon"],
                        missile_pos[0], missile_pos[1]
                    )
                    if dist <= interceptor.range_km:
                        return True
            return False
        
        return True
    
    def calculate_intercept_probability(self, missile: Missile, interceptor_type: str) -> float:
        """
        Calculate probability of successful intercept.
        
        Args:
            missile: The target missile
            interceptor_type: Type of interceptor
            
        Returns:
            Probability between 0 and 1
        """
        interceptor = self.inventory.get(interceptor_type)
        if not interceptor:
            return 0.0
        
        # Base probability
        prob = interceptor.success_base
        
        # Phase modifier
        phase_mod = self.PHASE_MODIFIERS.get(missile.status, 0.8)
        prob *= phase_mod
        
        # Distance modifier (for short-range interceptors)
        if interceptor_type in ["THAAD", "Patriot"]:
            # Reduce probability if distance is great
            distance_penalty = min(0.2, missile.distance_km / 10000)
            prob -= distance_penalty
        
        # Multiple intercept modifier (shoot-look-shoot)
        # If we've already fired at this missile, probability increases
        if missile.id in self.pending_launches:
            prob *= 1.2  # 20% bonus for second shot
        
        return max(0.1, min(0.95, prob))
    
    def launch_interceptor(self, missile_id: str, interceptor_type: str) -> bool:
        """
        Launch an interceptor at a missile.
        
        Args:
            missile_id: ID of target missile
            interceptor_type: Type of interceptor
            
        Returns:
            True if launch successful, False if not available
        """
        # Check availability
        if self.get_available(interceptor_type) <= 0:
            return False
        
        # Find missile
        missile = self.game_state.get_missile_by_id(missile_id)
        if not missile:
            return False
        
        # Check if can intercept
        if not self.can_intercept(missile, interceptor_type):
            return False
        
        # Decrement inventory
        self.inventory[interceptor_type].available -= 1
        
        # Track pending launch
        self.pending_launches[missile_id] = interceptor_type
        
        # Launch interceptor through game state
        self.game_state.launch_interceptor(missile_id, interceptor_type)
        
        return True
    
    def auto_intercept(self, missile: Missile, priority: str = "best") -> Optional[str]:
        """
        Automatically choose best interceptor for a missile.
        
        Args:
            missile: The target missile
            priority: Strategy ("best", "fastest", "cheapest")
            
        Returns:
            Interceptor type used, or None if none available
        """
        # Get available interceptor types
        available = []
        
        for itype in ["GBI", "THAAD", "Patriot"]:
            if self.can_intercept(missile, itype):
                prob = self.calculate_intercept_probability(missile, itype)
                available.append((itype, prob))
        
        if not available:
            return None
        
        # Sort by strategy
        if priority == "best":
            # Highest success probability
            available.sort(key=lambda x: x[1], reverse=True)
        elif priority == "fastest":
            # Fastest interceptor (THAAD > Patriot > GBI)
            speed_order = {"THAAD": 0, "Patriot": 1, "GBI": 2}
            available.sort(key=lambda x: speed_order.get(x[0], 99))
        elif priority == "cheapest":
            # Most available (Patriot > THAAD > GBI)
            available.sort(key=lambda x: self.get_total(x[0]), reverse=True)
        
        # Try to launch best option
        for itype, _ in available:
            if self.launch_interceptor(missile.id, itype):
                return itype
        
        return None
    
    def get_inventory_status(self) -> Dict:
        """Get current inventory status."""
        return {
            name: {
                "total": interceptor.total,
                "available": interceptor.available,
                "success_rate": interceptor.success_base
            }
            for name, interceptor in self.inventory.items()
        }
    
    def restore_interceptor(self, interceptor_type: str) -> None:
        """Restore an interceptor (for testing/debugging)."""
        if interceptor_type in self.inventory:
            self.inventory[interceptor_type].available = min(
                self.inventory[interceptor_type].total,
                self.inventory[interceptor_type].available + 1
            )