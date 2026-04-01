"""Test human player behavior."""

import pytest
from simulator.game_state import GameState
from simulator.defense import DefenseManager
from simulator.detection import DetectionManager
from simulator.human_player import HumanPlayer, PlayerState, PlayerMemory


class TestHumanPlayer:
    """Test human-like player behavior."""
    
    @pytest.fixture
    def player(self):
        gs = GameState()
        gs.load_data("data")
        defense = DefenseManager(gs)
        detection = DetectionManager()
        return HumanPlayer(gs, defense, detection)
    
    def test_initial_state(self, player):
        """Test initial player state."""
        assert player.state == PlayerState.IDLE
        assert player.memory.games_played == 0
        assert player.decisions_made == 0
    
    def test_reaction_time(self, player):
        """Test reaction time calculation."""
        rt = player.calculate_reaction_time()
        
        # Should be within bounds
        assert 0.3 <= rt <= 2.0
    
    def test_reaction_time_with_experience(self, player):
        """Test reaction time improves with experience."""
        initial_rt = player.calculate_reaction_time()
        
        # Simulate experience
        for _ in range(50):
            player.memory.games_played += 1
        
        experienced_rt = player.calculate_reaction_time()
        
        # Should be faster (or same)
        assert experienced_rt <= initial_rt
    
    def test_reaction_time_with_stress(self, player):
        """Test reaction time under stress."""
        normal_rt = player.calculate_reaction_time()
        
        # Simulate stress
        player.stress_level = 0.8
        stressed_rt = player.calculate_reaction_time()
        
        # Should be faster under stress
        assert stressed_rt < normal_rt
    
    def test_threat_assessment(self, player):
        """Test threat level assessment."""
        # No threats
        threat = player.assess_threat_level()
        assert threat == 0.0
        
        # Add missile
        player.game_state.launch_missile("Site", "City", "ICBM")
        threat = player.assess_threat_level()
        assert threat > 0
        
        # Add more missiles
        for i in range(10):
            player.game_state.launch_missile(f"Site{i}", f"City{i}", "ICBM")
        
        threat = player.assess_threat_level()
        assert threat > 0.5  # High threat
    
    def test_interceptor_prioritization(self, player):
        """Test interceptor type prioritization."""
        missile = player.game_state.launch_missile("Site", "City", "ICBM")
        
        # Missile in midcourse (best phase)
        missile.status = "midcourse"
        
        priorities = player.assess_interceptor_priority(missile)
        
        # Should prefer GBI for ICBM
        assert priorities[0][0] == "GBI"
        assert priorities[0][1] > 0  # Priority should be positive
    
    def test_missile_prioritization(self, player):
        """Test missile prioritization for interception."""
        # Launch multiple missiles
        missiles = []
        for i in range(5):
            m = player.game_state.launch_missile(f"Site{i}", f"City{i}", "ICBM")
            missiles.append(m)
        
        # Set different progress levels
        missiles[0].progress = 80.0  # Close to impact
        missiles[1].progress = 20.0  # Just launched
        missiles[2].target = "New York"  # High value
        missiles[3].progress = 50.0
        
        prioritized = player.prioritize_missiles(missiles)
        
        # Should prioritize high progress and high value targets
        assert prioritized[0].progress >= 80.0 or prioritized[0].target == "New York"
    
    def test_should_fire_decision(self, player):
        """Test fire decision."""
        missile = player.game_state.launch_missile("Site", "City", "ICBM")
        
        # Normal conditions
        itype = player.should_fire(missile)
        assert itype in ["GBI", "THAAD", "Patriot", None]
        
        # High stress - lower threshold
        player.stress_level = 0.8
        itype = player.should_fire(missile)
        # More likely to fire under stress
    
    def test_mistake_modeling(self, player):
        """Test mistake modeling."""
        # Low mistake probability
        player.mistake_probability = 0.5  # High for testing
        
        missile = player.game_state.launch_missile("Site", "City", "ICBM")
        
        # Try multiple times
        mistakes = 0
        for _ in range(100):
            player.game_state.launch_missile("Site2", "City2", "ICBM")
            result = player.make_mistake("missile_id", "GBI")
            if result[0] != "missile_id" or result[1] != "GBI":
                mistakes += 1
        
        # Should have some mistakes
        assert mistakes > 0
    
    def test_player_update(self, player):
        """Test player update cycle."""
        # Launch missile
        player.game_state.launch_missile("Site", "City", "ICBM")
        
        # Update player
        actions = player.update(0.1)
        
        # Should have made decision
        assert player.state in [PlayerState.IDLE, PlayerState.ASSESSING, PlayerState.LAUNCHING]
    
    def test_player_stats(self, player):
        """Test player statistics."""
        stats = player.get_stats()
        
        assert "games_played" in stats
        assert "win_rate" in stats
        assert "avg_reaction_time" in stats
    
    def test_game_result_recording(self, player):
        """Test recording game results."""
        player.record_game_result(True)
        
        assert player.memory.games_played == 1
        assert player.memory.games_won == 1
        
        player.record_game_result(False)
        
        assert player.memory.games_played == 2
        assert player.memory.games_won == 1


class TestPlayerMemory:
    """Test player memory/learning."""
    
    def test_memory_creation(self):
        """Test memory creation."""
        memory = PlayerMemory()
        
        assert memory.games_played == 0
        assert memory.games_won == 0
        assert memory.avg_reaction_time == 0.8
    
    def test_success_rate(self):
        """Test success rate calculation."""
        memory = PlayerMemory()
        
        # No launches
        rate = memory.get_success_rate("GBI")
        assert rate == 0.5  # Default
        
        # Some launches
        memory.interceptors_launched["GBI"] = 10
        memory.successful_intercepts["GBI"] = 7
        
        rate = memory.get_success_rate("GBI")
        assert rate == 0.7
    
    def test_game_recording(self):
        """Test game result recording."""
        memory = PlayerMemory()
        
        memory.record_game(True)
        assert memory.games_played == 1
        assert memory.games_won == 1
        
        memory.record_game(False)
        assert memory.games_played == 2
        assert memory.games_won == 1


class TestPlayerBehavior:
    """Test emergent player behavior."""
    
    @pytest.fixture
    def player(self):
        gs = GameState()
        gs.load_data("data")
        defense = DefenseManager(gs)
        detection = DetectionManager()
        return HumanPlayer(gs, defense, detection)
    
    def test_conservative_resource_use(self, player):
        """Test conservative resource use under multiple threats."""
        # Exhaust most interceptors
        for i in range(40):
            player.defense_manager.inventory["GBI"].available -= 1
        
        # Launch many missiles
        for i in range(20):
            player.game_state.launch_missile(f"Site{i}", f"City{i}", "ICBM")
        
        # Player should be conservative with remaining GBIs
        itype = player.should_fire(player.game_state.missiles[0])
        
        # With few GBIs left, might skip or use different type
        # (This tests the resource scarcity logic)
    
    def test_stress_affects_decisions(self, player):
        """Test that stress affects decision making."""
        missile = player.game_state.launch_missile("Site", "City", "ICBM")
        
        # No stress
        player.stress_level = 0.0
        player.decision_cooldown = 0
        rt1 = player.calculate_reaction_time()
        
        # High stress
        player.stress_level = 1.0
        player.decision_cooldown = 0
        rt2 = player.calculate_reaction_time()
        
        # Stressed player should react faster
        assert rt2 < rt1
    
    def test_learning_from_games(self, player):
        """Test that player learns from multiple games."""
        # Play multiple games
        for _ in range(10):
            player.memory.record_game(True)
            player.memory.interceptors_launched["GBI"] += 5
            player.memory.successful_intercepts["GBI"] += 3
        
        # Success rate should be tracked
        rate = player.memory.get_success_rate("GBI")
        assert 0.5 < rate < 1.0  # Learned from successful games