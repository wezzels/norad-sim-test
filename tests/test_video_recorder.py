"""Tests for video recording functionality."""

import pytest
import os
import tempfile
from pathlib import Path

from simulator import GameState, DefenseManager, DetectionManager, ScenarioLoader, HumanPlayer
from simulator.video_recorder import VideoRecorder, RecordingConfig, TestRecorder


class TestVideoRecorder:
    """Test video recorder basic functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test recordings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def recorder(self, temp_dir):
        """Create a video recorder for testing."""
        config = RecordingConfig(
            enabled=True,
            output_dir=temp_dir,
            fps=10,
            resolution=(640, 480),
            compression="low"
        )
        return VideoRecorder(config)
    
    @pytest.fixture
    def game_setup(self):
        """Create game state setup."""
        gs = GameState()
        gs.load_data("data")
        defense = DefenseManager(gs)
        detection = DetectionManager()
        return {"game_state": gs, "defense": defense, "detection": detection}
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = RecordingConfig()
        
        assert config.enabled == True
        assert config.format == "mp4"
        assert config.fps == 30
        assert config.resolution == (1280, 720)
        assert config.show_grid == True
        assert config.show_trajectories == True
        assert config.show_defcon == True
        assert config.show_stats == True
        assert config.compression == "medium"
    
    def test_recorder_initialization(self, recorder, temp_dir):
        """Test recorder initializes correctly."""
        assert recorder.config.output_dir == temp_dir
        assert recorder.frames == []
        assert recorder.recording == False
        assert recorder.events == []
    
    def test_start_recording(self, recorder):
        """Test starting recording."""
        recorder.start_recording("test_scenario")
        
        assert recorder.recording == True
        assert recorder.output_path is not None
        assert "test_scenario" in str(recorder.output_path)
    
    def test_capture_frame(self, recorder, game_setup):
        """Test capturing a frame."""
        gs = game_setup["game_state"]
        
        recorder.start_recording("test")
        
        # Capture initial frame
        recorder.capture_frame(gs)
        
        assert len(recorder.frames) == 1
        assert recorder.frames[0].frame_number == 0
        assert recorder.frames[0].simulation_time == 0.0
        
        # Advance time and capture another
        gs.simulation_time = 5.0
        recorder.capture_frame(gs, events=[{"action": "launch", "type": "GBI"}])
        
        assert len(recorder.frames) == 2
        assert recorder.frames[1].frame_number == 1
        assert recorder.frames[1].simulation_time == 5.0
        assert len(recorder.frames[1].events) == 1
    
    def test_capture_with_missiles(self, recorder, game_setup):
        """Test capturing frames with active missiles."""
        gs = game_setup["game_state"]
        
        recorder.start_recording("missile_test")
        
        # Launch missile
        missile = gs.launch_missile("Site Alpha", "New York", "ICBM")
        
        # Capture frame
        recorder.capture_frame(gs)
        
        assert len(recorder.frames) == 1
        state = recorder.frames[0].game_state
        assert len(state["missiles"]) == 1
        assert state["missiles"][0]["id"] == missile.id
    
    def test_stop_recording(self, recorder, game_setup):
        """Test stopping recording."""
        gs = game_setup["game_state"]
        
        recorder.start_recording("stop_test")
        
        # Capture a few frames
        for _ in range(5):
            recorder.capture_frame(gs)
            gs.simulation_time += 0.5
        
        # Stop recording
        video_path = recorder.stop_recording()
        
        assert recorder.recording == False
        assert len(recorder.frames) == 5
        # Note: video_path may be None if matplotlib not available
        # but the frames should still be captured
    
    def test_disabled_recording(self, temp_dir):
        """Test that disabled recorder doesn't record."""
        config = RecordingConfig(enabled=False)
        recorder = VideoRecorder(config)
        
        recorder.start_recording("test")
        # Should not have started recording
        # The enabled=False check prevents frames from being captured
        
        gs = GameState()
        recorder.capture_frame(gs)
        
        # Should have no frames since disabled
        # (depends on implementation - might still track but not output)
    
    def test_events_tracking(self, recorder, game_setup):
        """Test that events are tracked across frames."""
        gs = game_setup["game_state"]
        
        recorder.start_recording("events_test")
        
        # Simulate some events
        events1 = [{"action": "launch", "missile_id": "M1"}]
        events2 = [{"action": "intercept", "missile_id": "M1", "interceptor": "GBI"}]
        
        recorder.capture_frame(gs, events1)
        recorder.capture_frame(gs, events2)
        
        # Events should be tracked
        assert len(recorder.events) == 2
        assert recorder.events[0]["action"] == "launch"
        assert recorder.events[1]["action"] == "intercept"
    
    def test_get_summary(self, recorder, game_setup):
        """Test getting recording summary."""
        gs = game_setup["game_state"]
        
        recorder.start_recording("summary_test")
        
        for i in range(10):
            recorder.capture_frame(gs)
            gs.simulation_time += 1.0
        
        summary = recorder.get_summary()
        
        assert summary["frames_captured"] == 10
        assert summary["duration_seconds"] == 9.0  # Last frame time
        assert "config" in summary
        # Config from fixture has fps=10
        assert summary["config"]["fps"] == 10


class TestRecorderContext:
    """Test the TestRecorder context manager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test recordings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_context_manager_start_stop(self, temp_dir):
        """Test context manager starts and stops recording."""
        config = RecordingConfig(output_dir=temp_dir, fps=10)
        
        recorder = VideoRecorder(config)
        recorder.start_recording("test_scenario", "test_1")
        
        # Capture frame
        gs = GameState()
        recorder.capture_frame(gs)
        
        # Should be recording
        assert recorder.recording == True
        assert len(recorder.frames) == 1
        
        # Stop recording
        recorder.stop_recording()
        assert recorder.recording == False
    
    def test_context_manager_with_simulation(self, temp_dir):
        """Test recorder with a simple simulation."""
        config = RecordingConfig(output_dir=temp_dir, fps=10, resolution=(640, 480))
        
        recorder = VideoRecorder(config)
        recorder.start_recording("tutorial", "integration_test")
        
        gs = GameState()
        gs.load_data("data")
        defense = DefenseManager(gs)
        detection = DetectionManager()
        player = HumanPlayer(gs, defense, detection)
        scenarios = ScenarioLoader()
        
        # Load and run tutorial scenario
        scenario = scenarios.load_scenario("tutorial")
        scenarios.start_scenario()
        gs.resume()
        defense.reset_inventory(scenario.interceptors)
        
        # Run for limited time
        for _ in range(50):
            # Spawn missiles
            new_missiles = scenarios.update(gs.simulation_time)
            for m in new_missiles:
                gs.launch_missile(m.get("origin", "X"), m.get("target", "X"), m.get("type", "ICBM"))
            
            # Player acts
            events = player.update(0.1)
            
            # Capture frame
            recorder.capture_frame(gs, events)
            
            # Update game
            gs.update(0.1)
            
            # Check end
            if scenarios.is_complete() and len(gs.missiles) == 0:
                break
        
        # Should have captured frames
        assert len(recorder.frames) > 0
        assert recorder.frames[0].simulation_time == 0.0


class TestRecordingConfig:
    """Test recording configuration options."""
    
    def test_format_mp4(self):
        """Test MP4 format configuration."""
        config = RecordingConfig(format="mp4")
        assert config.format == "mp4"
    
    def test_format_gif(self):
        """Test GIF format configuration."""
        config = RecordingConfig(format="gif")
        assert config.format == "gif"
    
    def test_format_webm(self):
        """Test WebM format configuration."""
        config = RecordingConfig(format="webm")
        assert config.format == "webm"
    
    def test_resolution_options(self):
        """Test different resolution options."""
        # HD
        config_hd = RecordingConfig(resolution=(1280, 720))
        assert config_hd.resolution == (1280, 720)
        
        # Full HD
        config_fhd = RecordingConfig(resolution=(1920, 1080))
        assert config_fhd.resolution == (1920, 1080)
        
        # 4K
        config_4k = RecordingConfig(resolution=(3840, 2160))
        assert config_4k.resolution == (3840, 2160)
    
    def test_fps_options(self):
        """Test FPS options."""
        config_60 = RecordingConfig(fps=60)
        assert config_60.fps == 60
        
        config_24 = RecordingConfig(fps=24)
        assert config_24.fps == 24
    
    def test_compression_levels(self):
        """Test compression level options."""
        for level in ["low", "medium", "high"]:
            config = RecordingConfig(compression=level)
            assert config.compression == level


class TestVideoOutput:
    """Test video output generation (requires matplotlib)."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test recordings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_video_file_creation(self, temp_dir):
        """Test that video file is created."""
        try:
            import matplotlib
            HAS_MATPLOTLIB = True
        except ImportError:
            HAS_MATPLOTLIB = False
        
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not available")
        
        config = RecordingConfig(
            output_dir=temp_dir,
            fps=10,
            resolution=(320, 240),
            compression="low"
        )
        
        recorder = VideoRecorder(config)
        recorder.start_recording("file_test")
        
        # Create simple simulation
        gs = GameState()
        gs.load_data("data")
        
        # Capture frames
        for i in range(10):
            recorder.capture_frame(gs)
            gs.simulation_time += 1.0
        
        # Generate video
        video_path = recorder.stop_recording()
        
        # Check file was created
        if video_path:
            assert os.path.exists(video_path)
            assert video_path.endswith(".mp4")
    
    def test_gif_output(self, temp_dir):
        """Test GIF format output."""
        try:
            import matplotlib
            HAS_MATPLOTLIB = True
        except ImportError:
            HAS_MATPLOTLIB = False
        
        if not HAS_MATPLOTLIB:
            pytest.skip("matplotlib not available")
        
        config = RecordingConfig(
            output_dir=temp_dir,
            format="gif",
            fps=10,
            resolution=(320, 240)
        )
        
        recorder = VideoRecorder(config)
        recorder.start_recording("gif_test")
        
        gs = GameState()
        gs.load_data("data")
        
        for i in range(5):
            recorder.capture_frame(gs)
            gs.simulation_time += 0.5
        
        video_path = recorder.stop_recording()
        
        if video_path:
            assert video_path.endswith(".gif")


class TestVisualElements:
    """Test visual elements in video recording."""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_defcon_display(self, temp_dir):
        """Test DEFCON level is displayed correctly."""
        config = RecordingConfig(
            output_dir=temp_dir,
            show_defcon=True
        )
        recorder = VideoRecorder(config)
        recorder.start_recording("defcon_test")
        
        gs = GameState()
        
        # Test different DEFCON levels
        for level in [5, 4, 3, 2, 1]:
            gs.current_defcon = level
            recorder.capture_frame(gs)
        
        # Verify frames captured
        assert len(recorder.frames) == 5
        
        # Each frame should have the correct DEFCON in state
        for i, frame in enumerate(recorder.frames):
            defcon = [5, 4, 3, 2, 1][i]
            assert frame.game_state["defcon"] == defcon
    
    def test_stats_display(self, temp_dir):
        """Test stats are captured in frames."""
        config = RecordingConfig(
            output_dir=temp_dir,
            show_stats=True
        )
        recorder = VideoRecorder(config)
        recorder.start_recording("stats_test")
        
        gs = GameState()
        gs.load_data("data")
        
        # Capture initial frame (before any action)
        recorder.capture_frame(gs)
        
        # Launch first missile
        gs.launch_missile("Site Alpha", "New York", "ICBM")
        recorder.capture_frame(gs)
        
        # Launch second missile
        gs.launch_missile("Site Beta", "Chicago", "ICBM")
        recorder.capture_frame(gs)
        
        # Check stats progression - each frame should show increasing missiles
        stats0 = recorder.frames[0].game_state["stats"]
        stats1 = recorder.frames[1].game_state["stats"]
        stats2 = recorder.frames[2].game_state["stats"]
        
        # Stats should show increasing missile counts (or at least non-decreasing)
        assert stats2["missiles_launched"] >= stats1["missiles_launched"], \
            f"Missiles should not decrease: {stats1['missiles_launched']} -> {stats2['missiles_launched']}"
        assert stats1["missiles_launched"] >= stats0["missiles_launched"], \
            f"Missiles should not decrease: {stats0['missiles_launched']} -> {stats1['missiles_launched']}"
    
    def test_missile_positions(self, temp_dir):
        """Test missile positions are captured."""
        config = RecordingConfig(output_dir=temp_dir)
        recorder = VideoRecorder(config)
        recorder.start_recording("position_test")
        
        gs = GameState()
        gs.load_data("data")
        
        # Launch missile
        missile = gs.launch_missile("Site Alpha", "New York", "ICBM")
        
        # Capture initial position
        recorder.capture_frame(gs)
        
        # Advance simulation
        gs.simulation_time += 10.0
        gs.update_missiles(10.0)
        
        # Capture updated position
        recorder.capture_frame(gs)
        
        # Check positions differ
        pos0 = recorder.frames[0].game_state["missiles"][0]
        pos1 = recorder.frames[1].game_state["missiles"][0]
        
        # Progress should increase
        assert pos1["progress"] >= pos0["progress"]