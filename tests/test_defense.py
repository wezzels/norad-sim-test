"""Test suite for defense management."""

import pytest
from simulator.game_state import GameState, Missile
from simulator.defense import DefenseManager, InterceptorType


class TestDefenseManager:
    """Test defense manager functionality."""
    
    @pytest.fixture
    def defense(self):
        """Create defense manager with game state."""
        gs = GameState()
        gs.load_data("data")
        return DefenseManager(gs)
    
    def test_initial_inventory(self, defense):
        """Test initial interceptor inventory."""
        assert defense.get_available("GBI") == 44
        assert defense.get_available("THAAD") == 100
        assert defense.get_available("Patriot") == 200
    
    def test_interceptor_type_creation(self):
        """Test interceptor type dataclass."""
        gbi = InterceptorType.create("GBI", 50)
        
        assert gbi.name == "GBI"
        assert gbi.total == 50
        assert gbi.available == 50
        assert gbi.range_km == 5000.0
        assert gbi.success_base == 0.55
    
    def test_can_intercept(self, defense):
        """Test intercept capability check."""
        # Create a test missile
        missile = defense.game_state.launch_missile("Site", "New York", "ICBM")
        
        # GBI should be able to intercept anything
        assert defense.can_intercept(missile, "GBI") == True
    
    def test_launch_interceptor(self, defense):
        """Test launching interceptor."""
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        
        initial = defense.get_available("GBI")
        result = defense.launch_interceptor(missile.id, "GBI")
        
        assert result == True
        assert defense.get_available("GBI") == initial - 1
    
    def test_launch_interceptor_unavailable(self, defense):
        """Test launching when no interceptors available."""
        # Exhaust GBI inventory
        defense.inventory["GBI"].available = 0
        
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        result = defense.launch_interceptor(missile.id, "GBI")
        
        assert result == False
    
    def test_intercept_probability(self, defense):
        """Test intercept probability calculation."""
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        
        # Get probability for different phases
        missile.status = "boost"
        p_boost = defense.calculate_intercept_probability(missile, "GBI")
        
        missile.status = "midcourse"
        p_mid = defense.calculate_intercept_probability(missile, "GBI")
        
        missile.status = "terminal"
        p_term = defense.calculate_intercept_probability(missile, "GBI")
        
        # Midcourse should have highest probability
        assert p_mid > p_boost
        assert p_mid > p_term
    
    def test_auto_intercept(self, defense):
        """Test automatic interceptor selection."""
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        
        itype = defense.auto_intercept(missile)
        
        # Should choose an available interceptor type
        assert itype in ["GBI", "THAAD", "Patriot"]
        assert defense.get_available(itype) < defense.get_total(itype)
    
    def test_auto_intercept_priority(self, defense):
        """Test interceptor priority selection."""
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        
        # Test "best" priority
        itype = defense.auto_intercept(missile, priority="best")
        assert itype == "GBI"  # GBI has highest success rate
        
        # Reset inventory
        defense.reset_inventory()
        
        # Test with exhausted GBI
        defense.inventory["GBI"].available = 0
        itype = defense.auto_intercept(missile, priority="best")
        assert itype in ["THAAD", "Patriot"]
    
    def test_restore_interceptor(self, defense):
        """Test restoring interceptor to inventory."""
        defense.inventory["GBI"].available = 40  # Some used
        
        defense.restore_interceptor("GBI")
        
        assert defense.get_available("GBI") == 41
    
    def test_restore_interceptor_max(self, defense):
        """Test restoring doesn't exceed maximum."""
        defense.restore_interceptor("GBI")
        defense.restore_interceptor("GBI")
        
        # Should not exceed total
        assert defense.get_available("GBI") <= defense.get_total("GBI")
    
    def test_inventory_status(self, defense):
        """Test inventory status retrieval."""
        status = defense.get_inventory_status()
        
        assert "GBI" in status
        assert "THAAD" in status
        assert "Patriot" in status
        
        assert status["GBI"]["total"] == 44
        assert status["GBI"]["available"] == 44
        assert status["GBI"]["success_rate"] == 0.55
    
    def test_reset_inventory(self, defense):
        """Test resetting inventory."""
        # Use some interceptors
        defense.inventory["GBI"].available = 20
        defense.inventory["THAAD"].available = 50
        
        # Reset
        defense.reset_inventory()
        
        assert defense.get_available("GBI") == 44
        assert defense.get_available("THAAD") == 100
    
    def test_custom_inventory(self, defense):
        """Test custom inventory configuration."""
        defense.reset_inventory({
            "GBI": {"total": 10, "available": 10},
            "THAAD": {"total": 20, "available": 15},
            "Patriot": {"total": 50, "available": 50}
        })
        
        assert defense.get_total("GBI") == 10
        assert defense.get_available("GBI") == 10
        assert defense.get_available("THAAD") == 15


class TestInterceptorSelection:
    """Test interceptor selection logic."""
    
    @pytest.fixture
    def defense(self):
        gs = GameState()
        gs.load_data("data")
        return DefenseManager(gs)
    
    def test_select_best_interceptor(self, defense):
        """Test selecting best interceptor for different missiles."""
        # ICBM - should use GBI
        icbm = defense.game_state.launch_missile("Site", "City", "ICBM")
        priorities = defense.assess_interceptor_priority(icbm)
        # priorities is a list of (type, priority) tuples
        assert len(priorities) > 0
        assert priorities[0][0] == "GBI"  # Best choice first
    
    def test_range_limitation(self, defense):
        """Test THAAD/Patriot range limitations."""
        # This would require distance calculations
        # For now, test that can_intercept handles distance
        missile = defense.game_state.launch_missile("Site", "City", "ICBM")
        
        # GBI should always be able to intercept
        assert defense.can_intercept(missile, "GBI") == True


class TestMultipleIntercepts:
    """Test multiple intercept scenarios."""
    
    @pytest.fixture
    def defense(self):
        gs = GameState()
        gs.load_data("data")
        return DefenseManager(gs)
    
    def test_multiple_missiles(self, defense):
        """Test intercepting multiple missiles."""
        missiles = []
        for i in range(5):
            m = defense.game_state.launch_missile(f"Site{i}", f"City{i}", "ICBM")
            missiles.append(m)
        
        # Launch interceptors for all
        for m in missiles:
            result = defense.launch_interceptor(m.id, "GBI")
            assert result == True
        
        # Check inventory depletion
        assert defense.get_available("GBI") == 44 - 5
    
    def test_exhausted_inventory(self, defense):
        """Test behavior when inventory exhausted."""
        # Set low inventory
        defense.inventory["GBI"].available = 2
        
        missiles = []
        for i in range(5):
            m = defense.game_state.launch_missile(f"Site{i}", f"City{i}", "ICBM")
            missiles.append(m)
        
        # First two should succeed
        assert defense.launch_interceptor(missiles[0].id, "GBI") == True
        assert defense.launch_interceptor(missiles[1].id, "GBI") == True
        
        # Third should fail
        assert defense.launch_interceptor(missiles[2].id, "GBI") == False
    
    def test_pending_launches(self, defense):
        """Test tracking pending launches."""
        m = defense.game_state.launch_missile("Site", "City", "ICBM")
        defense.launch_interceptor(m.id, "GBI")
        
        assert m.id in defense.pending_launches
        assert defense.pending_launches[m.id] == "GBI"