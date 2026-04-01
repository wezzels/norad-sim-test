"""Test suite for game state management."""

import pytest
from simulator.game_state import GameState, Missile, Interceptor, DEFCON


class TestGameState:
    """Test game state functionality."""
    
    @pytest.fixture
    def game_state(self):
        """Create a fresh game state for each test."""
        gs = GameState()
        gs.load_data("data")  # Will use defaults if no data
        return gs
    
    def test_initial_state(self, game_state):
        """Test initial game state values."""
        assert game_state.paused == False
        assert game_state.speed_multiplier == 1.0
        assert game_state.current_defcon == 3
        assert game_state.simulation_time == 0.0
        assert len(game_state.missiles) == 0
        assert len(game_state.interceptors) == 0
        assert game_state.stats["missiles_launched"] == 0
    
    def test_pause_resume(self, game_state):
        """Test pause/resume functionality."""
        game_state.pause()
        assert game_state.paused == True
        
        game_state.resume()
        assert game_state.paused == False
    
    def test_speed_control(self, game_state):
        """Test speed multiplier."""
        game_state.set_speed(2.0)
        assert game_state.speed_multiplier == 2.0
        
        game_state.set_speed(0.1)
        assert game_state.speed_multiplier == 0.1  # Minimum
        
        game_state.set_speed(200.0)
        assert game_state.speed_multiplier == 100.0  # Maximum
    
    def test_defcon_changes(self, game_state):
        """Test DEFCON level changes."""
        # Valid range
        game_state.set_defcon(1)
        assert game_state.current_defcon == 1
        
        game_state.set_defcon(5)
        assert game_state.current_defcon == 5
        
        # Out of range
        game_state.set_defcon(0)
        assert game_state.current_defcon == 1  # Clamped
        
        game_state.set_defcon(10)
        assert game_state.current_defcon == 5  # Clamped
    
    def test_reset_state(self, game_state):
        """Test state reset."""
        game_state.set_defcon(1)
        game_state.set_speed(5.0)
        game_state.simulation_time = 100.0
        game_state.stats["missiles_launched"] = 10
        
        game_state.reset_state()
        
        assert game_state.current_defcon == 3
        assert game_state.speed_multiplier == 1.0
        assert game_state.simulation_time == 0.0
        assert game_state.stats["missiles_launched"] == 0
    
    def test_launch_missile(self, game_state):
        """Test missile launch."""
        missile = game_state.launch_missile(
            "Test Site Alpha",
            "Test City Beta",
            "ICBM"
        )
        
        assert missile is not None
        assert missile.origin == "Test Site Alpha"
        assert missile.target == "Test City Beta"
        assert missile.missile_type == "ICBM"
        assert missile.status == "boost"
        assert len(game_state.missiles) == 1
        assert game_state.stats["missiles_launched"] == 1
    
    def test_launch_interceptor(self, game_state):
        """Test interceptor launch."""
        # First launch a missile
        missile = game_state.launch_missile("Site", "City", "ICBM")
        
        # Then launch interceptor
        interceptor = game_state.launch_interceptor(missile.id, "GBI")
        
        assert interceptor is not None
        assert interceptor.missile_id == missile.id
        assert interceptor.interceptor_type == "GBI"
        assert len(game_state.interceptors) == 1
    
    def test_missile_update(self, game_state):
        """Test missile position updates."""
        missile = game_state.launch_missile("Site", "City", "ICBM")
        
        # Simulate time passing
        game_state.update(10.0)
        
        # Missile should have progressed
        assert missile.progress > 0
        assert missile.altitude > 0
        assert missile.speed > 0
    
    def test_interceptor_update(self, game_state):
        """Test interceptor progress."""
        missile = game_state.launch_missile("Site", "City", "ICBM")
        interceptor = game_state.launch_interceptor(missile.id, "GBI")
        
        initial_progress = interceptor.progress
        
        # Simulate time
        game_state.update(5.0)
        
        # Interceptor should have progressed
        assert interceptor.progress > initial_progress
    
    def test_missile_impact(self, game_state):
        """Test missile impact and detonation."""
        missile = game_state.launch_missile("Site", "City", "ICBM")
        
        # Simulate full flight time
        game_state.update(missile.flight_time + 10.0)
        
        # Missile should be removed
        assert len(game_state.missiles) == 0
        
        # Detonation should be recorded
        assert len(game_state.detonations) == 1
        assert game_state.stats["cities_hit"] == 1
    
    def test_intercept_success(self, game_state):
        """Test successful interception."""
        missile = game_state.launch_missile("Site", "City", "ICBM")
        
        # Force interceptor success
        interceptor = game_state.launch_interceptor(missile.id, "GBI")
        interceptor.success = True
        
        # Update until interceptor completes
        game_state.update(20.0)
        
        # Missile should be marked intercepted
        assert missile.intercepted == True
        assert game_state.stats["missiles_intercepted"] == 1
    
    def test_get_state(self, game_state):
        """Test state serialization."""
        game_state.launch_missile("Site", "City", "ICBM")
        game_state.set_defcon(2)
        
        state = game_state.get_state()
        
        assert "paused" in state
        assert "speed" in state
        assert "defcon" in state
        assert "missiles" in state
        assert "stats" in state
        assert state["defcon"] == 2


class TestMissile:
    """Test missile dataclass."""
    
    def test_missile_creation(self):
        """Test missile creation."""
        missile = Missile(
            id="TEST-001",
            origin="Launch Site",
            target="Target City",
            missile_type="ICBM"
        )
        
        assert missile.id == "TEST-001"
        assert missile.status == "boost"
        assert missile.intercepted == False
    
    def test_missile_defaults(self):
        """Test missile default values."""
        missile = Missile(
            id="TEST",
            origin="A",
            target="B",
            missile_type="ICBM"
        )
        
        assert missile.altitude == 0.0
        assert missile.progress == 0.0
        assert missile.warhead_yield >= 100


class TestDEFCON:
    """Test DEFCON enum."""
    
    def test_defcon_values(self):
        """Test DEFCON values."""
        assert DEFCON.NORMAL.value == 5
        assert DEFCON.MAXIMUM.value == 1
        assert DEFCON.AIR_FORCE_READY.value == 3


class TestGameStateCallbacks:
    """Test game state callback system."""
    
    @pytest.fixture
    def game_state(self):
        gs = GameState()
        gs.load_data("data")
        return gs
    
    def test_missile_launch_callback(self, game_state):
        """Test missile launch callback."""
        called = []
        
        def on_launch(missile):
            called.append(missile.id)
        
        game_state._on_missile_launched = on_launch
        game_state.launch_missile("Site", "City", "ICBM")
        
        assert len(called) == 1
    
    def test_defcon_callback(self, game_state):
        """Test DEFCON change callback."""
        called = []
        
        def on_defcon(level):
            called.append(level)
        
        game_state._on_defcon_change = on_defcon
        game_state.set_defcon(1)
        game_state.set_defcon(5)
        
        assert len(called) == 2
        assert called == [1, 5]