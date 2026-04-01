"""Human-like AI Player.

Emulates human gameplay patterns including reaction times,
decision making, mistakes, and learning.
"""

import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .game_state import GameState, Missile
from .defense import DefenseManager
from .detection import DetectionManager


class PlayerState(Enum):
    """Player states."""
    IDLE = "idle"
    ASSESSING = "assessing"
    TARGETING = "targeting"
    LAUNCHING = "launching"
    WAITING = "waiting"


@dataclass
class PlayerMemory:
    """Tracks player learning and preferences."""
    games_played: int = 0
    games_won: int = 0
    interceptors_launched: Dict[str, int] = field(default_factory=lambda: {"GBI": 0, "THAAD": 0, "Patriot": 0})
    successful_intercepts: Dict[str, int] = field(default_factory=lambda: {"GBI": 0, "THAAD": 0, "Patriot": 0})
    cities_lost: int = 0
    avg_reaction_time: float = 0.8  # Start with moderate reaction time
    
    def get_success_rate(self, interceptor_type: str) -> float:
        """Calculate success rate for an interceptor type."""
        launched = self.interceptors_launched.get(interceptor_type, 0)
        if launched == 0:
            return 0.5  # No data, assume 50%
        successful = self.successful_intercepts.get(interceptor_type, 0)
        return successful / launched
    
    def record_game(self, won: bool) -> None:
        """Record game outcome."""
        self.games_played += 1
        if won:
            self.games_won += 1


class HumanPlayer:
    """
    Human-like AI player for NORAD War Simulator.
    
    Emulates:
    - Variable reaction times (0.3-2.0 seconds)
    - Learning curve (improves with practice)
    - Stress response (faster decisions under threat)
    - Mistake modeling (occasional mis-targets)
    - Priority assessment (cities vs interceptors)
    - Resource management
    """
    
    # Reaction time parameters (in seconds)
    BASE_REACTION_TIME = 0.8
    MIN_REACTION_TIME = 0.3
    MAX_REACTION_TIME = 2.0
    STRESS_REDUCTION = 0.3  # How much faster under stress
    
    # Interceptor preferences
    INTERCEPTOR_PRIORITY = ["GBI", "THAAD", "Patriot"]  # Use most capable first
    
    # City priority weights
    HIGH_VALUE_CITIES = [
        "New York", "Washington DC", "Los Angeles", "Chicago",
        "San Francisco", "Seattle", "Boston", "Philadelphia"
    ]
    
    def __init__(self, game_state: GameState, defense_manager: DefenseManager,
                 detection_manager: DetectionManager):
        self.game_state = game_state
        self.defense_manager = defense_manager
        self.detection_manager = detection_manager
        
        # Player state
        self.state = PlayerState.IDLE
        self.memory = PlayerMemory()
        
        # Decision making
        self.target_queue: List[Tuple[str, str]] = []  # (missile_id, interceptor_type)
        self.last_decision_time: float = 0.0
        self.decision_cooldown: float = 0.0
        
        # Mistake modeling
        self.mistake_probability = 0.05  # 5% chance of mis-target
        self.mistake_types = ["wrong_missile", "wrong_interceptor", "delay", "skip"]
        
        # Stress tracking
        self.threat_level = 0.0  # 0-1, increases with active threats
        self.stress_level = 0.0
        
        # Performance tracking
        self.reaction_times: List[float] = []
        self.decisions_made: int = 0
    
    def calculate_reaction_time(self) -> float:
        """
        Calculate reaction time based on experience and stress.
        
        Returns:
            Reaction time in seconds
        """
        # Base reaction time improves with experience
        experience_factor = max(0.7, 1.0 - self.memory.games_played * 0.02)
        base = self.BASE_REACTION_TIME * experience_factor
        
        # Stress reduces reaction time (faster under pressure)
        stress_bonus = self.stress_level * self.STRESS_REDUCTION
        base -= stress_bonus
        
        # Add random variation (human inconsistency)
        variation = random.uniform(-0.2, 0.5)
        reaction_time = base + variation
        
        # Clamp to valid range
        return max(self.MIN_REACTION_TIME, min(self.MAX_REACTION_TIME, reaction_time))
    
    def assess_threat_level(self) -> float:
        """
        Calculate current threat level (0-1).
        
        Higher when:
        - More active missiles
        - Missiles closer to targets
        - More high-value cities targeted
        """
        threat = 0.0
        
        # Base threat from number of missiles
        num_missiles = len(self.game_state.missiles)
        threat += min(0.4, num_missiles * 0.05)
        
        # Threat from progress (how close missiles are to impact)
        for missile in self.game_state.missiles:
            if missile.intercepted:
                continue
            threat += missile.progress / 500.0  # Progress contribution
            if missile.progress > 50:
                threat += 0.1  # Extra threat for close missiles
        
        # High-value city threat
        for missile in self.game_state.missiles:
            if missile.target in self.HIGH_VALUE_CITIES:
                threat += 0.05
        
        # Reduce threat if we have interceptors
        total_available = sum(
            self.defense_manager.get_available(t) 
            for t in self.INTERCEPTOR_PRIORITY
        )
        threat -= min(0.3, total_available * 0.01)
        
        return max(0.0, min(1.0, threat))
    
    def assess_interceptor_priority(self, missile: Missile) -> List[Tuple[str, float]]:
        """
        Determine which interceptor type to use and calculate priority.
        
        Args:
            missile: The target missile
            
        Returns:
            List of (interceptor_type, priority) tuples, sorted by priority
        """
        priorities = []
        
        for itype in self.INTERCEPTOR_PRIORITY:
            # Check availability
            available = self.defense_manager.get_available(itype)
            if available <= 0:
                continue
            
            # Can we intercept this missile?
            if not self.defense_manager.can_intercept(missile, itype):
                continue
            
            # Calculate priority
            prob = self.defense_manager.calculate_intercept_probability(missile, itype)
            
            # Factor in historical success rate
            historical_rate = self.memory.get_success_rate(itype)
            adjusted_prob = prob * 0.7 + historical_rate * 0.3
            
            # Factor in resource scarcity (save rare interceptors)
            total = self.defense_manager.get_total(itype)
            scarcity_bonus = 1.0 - (available / total) * 0.3
            
            priority = adjusted_prob * scarcity_bonus
            
            # Penalty for using expensive interceptors on easy targets
            if itype == "GBI" and missile.missile_type == "SRBM":
                priority *= 0.7  # Don't waste GBIs on short-range missiles
            
            priorities.append((itype, priority))
        
        # Sort by priority (highest first)
        priorities.sort(key=lambda x: x[1], reverse=True)
        return priorities
    
    def prioritize_missiles(self, missiles: List[Missile]) -> List[Missile]:
        """
        Prioritize missiles for interception.
        
        Priority factors:
        - Time to impact (progress)
        - Target importance
        - Interceptability (phase)
        """
        scored_missiles = []
        
        for missile in missiles:
            if missile.intercepted:
                continue
            
            score = 0.0
            
            # Time to impact (higher progress = higher priority)
            score += missile.progress
            
            # Target importance
            if missile.target in self.HIGH_VALUE_CITIES:
                score += 20
            
            # Phase bonus (midcourse is best for interception)
            if missile.status == "midcourse":
                score += 15
            elif missile.status == "boost":
                score += 5  # Hard to intercept
            else:  # terminal
                score += 10  # Last chance
            
            # Warhead yield (bigger = higher priority)
            score += missile.warhead_yield / 100.0
            
            # Distance penalty (harder to intercept distant threats)
            score -= missile.distance_km / 1000.0
            
            scored_missiles.append((missile, score))
        
        # Sort by score (highest first)
        scored_missiles.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_missiles]
    
    def should_fire(self, missile: Missile) -> Optional[str]:
        """
        Determine if we should fire at a missile and with what.
        
        Args:
            missile: Target missile
            
        Returns:
            Interceptor type to use, or None if shouldn't fire
        """
        # Get interceptor priorities
        priorities = self.assess_interceptor_priority(missile)
        
        if not priorities:
            return None
        
        # Best interceptor
        best_type, best_priority = priorities[0]
        
        # Decision threshold based on threat level
        threshold = 0.3 - self.stress_level * 0.1  # Lower threshold when stressed
        
        if best_priority >= threshold:
            # Check if we should save interceptors for better opportunities
            if len(self.game_state.missiles) > 5:
                # Multiple threats - be more conservative
                if best_priority < 0.5 and best_type == "GBI":
                    # Don't waste GBIs on low-probability shots
                    return None
            
            return best_type
        
        return None
    
    def make_mistake(self, missile_id: str, interceptor_type: str) -> Tuple[str, str]:
        """
        Potentially make a mistake in targeting.
        
        Args:
            missile_id: Intended target
            interceptor_type: Intended interceptor
            
        Returns:
            (actual_missile_id, actual_interceptor_type)
        """
        if random.random() > self.mistake_probability:
            return missile_id, interceptor_type
        
        # Choose mistake type
        mistake = random.choice(self.mistake_types)
        
        if mistake == "wrong_missile" and len(self.game_state.missiles) > 1:
            # Target wrong missile
            others = [m.id for m in self.game_state.missiles if m.id != missile_id and not m.intercepted]
            if others:
                return random.choice(others), interceptor_type
        
        elif mistake == "wrong_interceptor":
            # Use wrong interceptor
            available = [t for t in self.INTERCEPTOR_PRIORITY 
                        if self.defense_manager.get_available(t) > 0]
            if len(available) > 1:
                return missile_id, random.choice(available)
        
        elif mistake == "delay":
            # Add delay (handled in timing)
            pass
        
        # "skip" or "delay" - return original
        return missile_id, interceptor_type
    
    def update(self, delta: float) -> List[Dict]:
        """
        Update player state and make decisions.
        
        Args:
            delta: Time delta in seconds
            
        Returns:
            List of actions taken
        """
        actions = []
        
        # Update threat level
        self.threat_level = self.assess_threat_level()
        self.stress_level = min(1.0, self.threat_level * 1.5)
        
        # Check if we should make a decision
        current_time = self.game_state.simulation_time
        if current_time - self.last_decision_time < self.decision_cooldown:
            return actions
        
        # Calculate reaction time
        reaction_time = self.calculate_reaction_time()
        
        # Update cooldown based on reaction time
        self.decision_cooldown = reaction_time
        self.last_decision_time = current_time
        
        # Record reaction time
        self.reaction_times.append(reaction_time)
        if len(self.reaction_times) > 100:
            self.reaction_times.pop(0)
        
        # Get active missiles
        active_missiles = [m for m in self.game_state.missiles if not m.intercepted]
        
        if not active_missiles:
            self.state = PlayerState.IDLE
            return actions
        
        # Prioritize missiles
        prioritized = self.prioritize_missiles(active_missiles)
        
        # Make decisions for top threats
        self.state = PlayerState.ASSESSING
        
        # Process up to 3 missiles per update (human cognitive limit)
        for missile in prioritized[:3]:
            # Should we fire?
            interceptor_type = self.should_fire(missile)
            
            if interceptor_type:
                self.state = PlayerState.LAUNCHING
                
                # Potentially make a mistake
                target_id, itype = self.make_mistake(missile.id, interceptor_type)
                
                # Try to launch
                if self.defense_manager.launch_interceptor(target_id, itype):
                    self.memory.interceptors_launched[itype] += 1
                    self.decisions_made += 1
                    
                    actions.append({
                        "action": "launch_interceptor",
                        "missile_id": target_id,
                        "interceptor_type": itype,
                        "reaction_time": reaction_time,
                        "stress": self.stress_level
                    })
                    
                    # Brief cooldown between launches
                    self.decision_cooldown += 0.1
                    break
        
        return actions
    
    def record_game_result(self, won: bool) -> None:
        """Record the result of a game for learning."""
        self.memory.record_game(won)
        
        # Update average reaction time
        if self.reaction_times:
            self.memory.avg_reaction_time = sum(self.reaction_times) / len(self.reaction_times)
    
    def get_stats(self) -> Dict:
        """Get player statistics."""
        return {
            "games_played": self.memory.games_played,
            "win_rate": self.memory.games_won / max(1, self.memory.games_played),
            "decisions_made": self.decisions_made,
            "avg_reaction_time": self.memory.avg_reaction_time,
            "interceptors_launched": dict(self.memory.interceptors_launched),
            "current_threat_level": self.threat_level,
            "current_stress_level": self.stress_level
        }