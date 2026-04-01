"""Integration tests for full simulation."""

import pytest
from simulator import GameState, DefenseManager, DetectionManager, ScenarioLoader, HumanPlayer


class TestIntegration:
    """Integration tests for complete simulation."""
    
    @pytest.fixture
    def setup(self):
        """Create full simulation setup."""
        gs = GameState()
        gs.load_data("data")
        defense = DefenseManager(gs)
        detection = DetectionManager()
        player = HumanPlayer(gs, defense, detection)
        scenarios = ScenarioLoader()
        
        return {
            "game_state": gs,
            "defense": defense,
            "detection": detection,
            "player": player,
            "scenarios": scenarios
        }
    
    def test_tutorial_scenario(self, setup):
        """Test tutorial scenario completion."""
        gs = setup["game_state"]
        defense = setup["defense"]
        player = setup["player"]
        scenarios = setup["scenarios"]
        
        # Load tutorial
        scenario = scenarios.load_scenario("tutorial")
        assert scenario is not None
        assert scenario.name == "Tutorial: First Contact"
        
        # Start scenario
        scenarios.start_scenario()
        gs.resume()
        defense.reset_inventory(scenario.interceptors)
        
        # Run simulation
        for _ in range(100):  # Max iterations
            # Spawn missiles
            new_missiles = scenarios.update(gs.simulation_time)
            for m in new_missiles:
                gs.launch_missile(m.get("origin", "X"), m.get("target", "X"), m.get("type", "ICBM"))
            
            # Player acts
            player.update(0.1)
            
            # Update game
            gs.update(0.1)
            
            # Check end conditions
            if scenarios.is_complete() and len(gs.missiles) == 0:
                break
        
        # Tutorial should be completable
        assert gs.stats["missiles_launched"] > 0
    
    def test_cold_war_scenario(self, setup):
        """Test cold war scenario."""
        gs = setup["game_state"]
        defense = setup["defense"]
        player = setup["player"]
        scenarios = setup["scenarios"]
        
        scenario = scenarios.load_scenario("cold_war")
        assert scenario is not None
        assert scenario.difficulty == 2
        
        scenarios.start_scenario()
        gs.resume()
        defense.reset_inventory(scenario.interceptors)
        
        # Run for a while
        for _ in range(500):
            new_missiles = scenarios.update(gs.simulation_time)
            for m in new_missiles:
                gs.launch_missile(m.get("origin", "X"), m.get("target", "X"), m.get("type", "ICBM"))
            
            player.update(0.1)
            gs.update(0.1)
            
            if gs.simulation_time > 600:  # 10 minutes max
                break
        
        # Should have launched interceptors
        assert player.decisions_made > 0
    
    def test_player_learning(self, setup):
        """Test that player statistics are tracked."""
        player = setup["player"]
        
        # Simulate multiple games
        for _ in range(3):
            player.memory.record_game(True)
        
        assert player.memory.games_played == 3
        assert player.memory.games_won == 3
        
        # Simulate loss
        player.memory.record_game(False)
        assert player.memory.games_won == 3
        assert player.memory.games_played == 4
    
    def test_full_workflow(self, setup):
        """Test complete workflow from detection to intercept."""
        gs = setup["game_state"]
        defense = setup["defense"]
        detection = setup["detection"]
        player = setup["player"]
        
        # Launch missile
        missile = gs.launch_missile("Site", "New York", "ICBM")
        
        # Simulate detection
        for t in range(10):
            detections = detection.detect_missiles(gs.missiles, float(t))
            if detections:
                break
        
        # Player should intercept
        actions = player.update(0.1)
        
        # Check intercept happened
        assert len(actions) > 0 or len(gs.interceptors) > 0
    
    def test_resource_management(self, setup):
        """Test interceptor resource management."""
        gs = setup["game_state"]
        defense = setup["defense"]
        player = setup["player"]
        
        # Reset inventory
        defense.reset_inventory({"GBI": 10, "THAAD": 20, "Patriot": 30})
        
        # Launch many missiles
        for i in range(15):
            gs.launch_missile(f"Site{i}", f"City{i}", "ICBM")
        
        # Player should manage resources
        initial_total = sum(defense.get_available(t) for t in ["GBI", "THAAD", "Patriot"])
        
        for _ in range(20):
            player.update(0.1)
            gs.update(0.1)
        
        # Should have used some interceptors
        final_total = sum(defense.get_available(t) for t in ["GBI", "THAAD", "Patriot"])
        
        assert final_total < initial_total
    
    def test_threat_assessment(self, setup):
        """Test player threat assessment."""
        player = setup["player"]
        gs = setup["game_state"]
        
        # No missiles = low threat
        threat = player.assess_threat_level()
        assert threat == 0.0
        
        # Add missiles
        for i in range(5):
            gs.launch_missile(f"Site{i}", f"City{i}", "ICBM")
        
        threat = player.assess_threat_level()
        assert threat > 0
    
    def test_reaction_time_improvement(self, setup):
        """Test that reaction time improves with experience."""
        player = setup["player"]
        
        # New player has baseline reaction time
        initial_rt = player.calculate_reaction_time()
        
        # Simulate experience
        for _ in range(100):
            player.memory.games_played += 1
            player.reaction_times.append(player.calculate_reaction_time())
        
        # Experienced player should be faster
        experienced_rt = player.calculate_reaction_time()
        
        assert experienced_rt <= initial_rt


class TestScenarios:
    """Test scenario system."""
    
    def test_scenario_list(self):
        """Test listing scenarios."""
        loader = ScenarioLoader()
        scenarios = loader.get_available_scenarios()
        
        assert len(scenarios) > 0
        
        # Check all scenarios have required fields
        for s in scenarios:
            assert "id" in s
            assert "name" in s
            assert "difficulty" in s
    
    def test_all_scenarios_loadable(self):
        """Test all scenarios can be loaded."""
        loader = ScenarioLoader()
        scenarios = loader.get_available_scenarios()
        
        for s in scenarios:
            scenario = loader.load_scenario(s["id"])
            assert scenario is not None
            assert scenario.id == s["id"]
    
    def test_scenario_waves(self):
        """Test scenario wave system."""
        loader = ScenarioLoader()
        scenario = loader.load_scenario("tutorial")
        
        assert len(scenario.waves) > 0
        
        for wave in scenario.waves:
            assert len(wave.missiles) > 0
            assert wave.delay >= 0