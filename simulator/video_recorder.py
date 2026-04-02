"""Video Recorder for Test Sessions.

Records simulation sessions to video files using matplotlib for frame generation
and ffmpeg for encoding. Provides visual documentation of test runs.
"""

import os
import subprocess
import tempfile
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from .game_state import GameState, Missile, Interceptor


@dataclass
class RecordingConfig:
    """Configuration for video recording."""
    enabled: bool = True
    output_dir: str = "recordings"
    format: str = "mp4"  # mp4, gif, webm
    fps: int = 30
    resolution: Tuple[int, int] = (1280, 720)  # width, height
    show_grid: bool = True
    show_trajectories: bool = True
    show_defcon: bool = True
    show_stats: bool = True
    highlight_interceptions: bool = True
    compression: str = "medium"  # low, medium, high
    realtime_playback: bool = False  # True = 1 sim second = 1 video second
    geojson_path: str = ""  # Path to world GeoJSON (auto-detected if empty)


@dataclass
class Frame:
    """Single frame data."""
    frame_number: int
    simulation_time: float
    game_state: Dict
    events: List[Dict] = field(default_factory=list)


class WorldMap:
    """Loads and renders world map from GeoJSON."""
    
    def __init__(self, geojson_path: Optional[str] = None):
        self.countries = []
        self.loaded = False
        
        # Try to find GeoJSON file
        search_paths = [
            geojson_path,
            "/home/wez/stsgym-work/stsgym-maps/data/world.json",
            "data/world.json",
            "../stsgym-maps/data/world.json",
        ]
        
        for path in search_paths:
            if path and os.path.exists(path):
                self._load_geojson(path)
                break
    
    def _load_geojson(self, path: str) -> None:
        """Load GeoJSON world map."""
        try:
            with open(path) as f:
                data = json.load(f)
            
            features = data.get('features', [])
            for feature in features:
                props = feature.get('properties', {})
                name = props.get('name', props.get('NAME', 'Unknown'))
                geometry = feature.get('geometry', {})
                geom_type = geometry.get('type')
                coords = geometry.get('coordinates', [])
                
                if geom_type == 'Polygon':
                    self.countries.append({
                        'name': name,
                        'polygons': [coords]
                    })
                elif geom_type == 'MultiPolygon':
                    self.countries.append({
                        'name': name,
                        'polygons': coords
                    })
            
            self.loaded = True
        except Exception as e:
            print(f"Warning: Could not load GeoJSON from {path}: {e}")
            self.loaded = False
    
    def draw(self, ax, land_color: str = "#1a4a1a", alpha: float = 0.7) -> None:
        """Draw countries on matplotlib axes."""
        if not self.loaded:
            return
        
        for country in self.countries:
            for polygon in country['polygons']:
                # Polygon can be a list of rings (exterior + holes)
                if len(polygon) > 0:
                    # First ring is exterior
                    ring = polygon[0] if isinstance(polygon[0][0], list) and len(polygon[0][0]) == 2 else polygon
                    
                    try:
                        # Extract coordinates
                        if isinstance(ring[0][0], list):
                            # Nested list
                            lons = [pt[0] for pt in ring[0]]
                            lats = [pt[1] for pt in ring[0]]
                        else:
                            # Flat list of [lon, lat]
                            lons = [pt[0] for pt in ring]
                            lats = [pt[1] for pt in ring]
                        
                        ax.fill(lons, lats, color=land_color, alpha=alpha)
                        ax.plot(lons, lats, color=land_color, alpha=alpha + 0.1, linewidth=0.3)
                    except (IndexError, TypeError):
                        # Skip malformed polygons
                        pass


class VideoRecorder:
    """
    Records simulation sessions to video.
    
    Features:
    - Globe projection with missile/interceptor visualization
    - Event highlighting (launches, intercepts, impacts)
    - DEFCON and stats overlay
    - Trajectory trails
    - Multiple output formats
    """
    
    # Colors
    COLORS = {
        "background": "#0a0a1a",
        "land": "#1a4a1a",
        "ocean": "#0a1a2a",
        "missile_boost": "#ff4444",
        "missile_midcourse": "#ffaa00",
        "missile_terminal": "#ff0000",
        "interceptor": "#00ff00",
        "grid": "#333366",
        "text": "#ffffff",
        "highlight": "#ffff00",
        "city": "#00aaff",
        "launch_site": "#ff6600"
    }
    
    # DEFCON colors
    DEFCON_COLORS = {
        5: "#00ff00",  # Normal - green
        4: "#88ff00",  # Increased
        3: "#ffff00",  # Air Force Ready - yellow
        2: "#ff8800",  # Armed Forces Ready - orange
        1: "#ff0000"   # Maximum - red
    }
    
    def __init__(self, config: Optional[RecordingConfig] = None):
        self.config = config or RecordingConfig()
        self.frames: List[Frame] = []
        self.current_frame: Optional[Frame] = None
        self.recording = False
        self.start_time: float = 0.0
        self.output_path: Optional[Path] = None
        self.temp_dir: Optional[str] = None
        
        # Event tracking
        self.events: List[Dict] = []
        self.highlights: List[Dict] = []
        
        # World map from GeoJSON
        self.world_map = WorldMap(self.config.geojson_path)
        
        # City coordinates for visualization
        self._cities = self._load_default_cities()
        self._launch_sites = self._load_default_launch_sites()
    
    def _load_default_cities(self) -> Dict[str, Tuple[float, float]]:
        """Load default city coordinates."""
        return {
            "New York": (40.7128, -74.0060),
            "Los Angeles": (34.0522, -118.2437),
            "Chicago": (41.8781, -87.6298),
            "Houston": (29.7604, -95.3698),
            "Phoenix": (33.4484, -112.0740),
            "Philadelphia": (39.9526, -75.1652),
            "San Antonio": (29.4241, -98.4936),
            "San Diego": (32.7157, -117.1611),
            "Dallas": (32.7767, -96.7970),
            "San Jose": (37.3382, -121.8863),
            "Austin": (30.2672, -97.7431),
            "Jacksonville": (30.3322, -81.6557),
            "San Francisco": (37.7749, -122.4194),
            "Seattle": (47.6062, -122.3321),
            "Boston": (42.3601, -71.0589),
            "Washington DC": (38.9072, -77.0369),
            "Denver": (39.7392, -104.9903),
            "Miami": (25.7617, -80.1918),
            "Atlanta": (33.7490, -84.3880),
            "Detroit": (42.3314, -83.0458)
        }
    
    def _load_default_launch_sites(self) -> Dict[str, Tuple[float, float]]:
        """Load default launch site coordinates."""
        return {
            "Site Alpha": (41.0, 129.0),  # North Korea
            "Site Beta": (39.0, 125.0),  # North Korea
            "Site Gamma": (35.0, 50.0),  # Iran
            "Site Delta": (33.0, 44.0),  # Iraq
            "Site Epsilon": (55.0, 38.0),  # Russia
            "Site Zeta": (30.0, 112.0),  # China
            "Site Eta": (18.0, 47.0),  # Yemen
            "Site Theta": (28.0, 33.0),  # Egypt
            "Site Iota": (25.0, 55.0),  # UAE
            "Site Kappa": (22.0, 114.0)  # South China Sea
        }
    
    def start_recording(self, scenario_name: str = "test", test_name: str = "") -> None:
        """
        Start recording a new session.
        
        Args:
            scenario_name: Name of scenario being recorded
            test_name: Name of test being recorded
        """
        if not self.config.enabled:
            return
        
        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not available, video recording disabled")
            self.config.enabled = False
            return
        
        self.frames.clear()
        self.events.clear()
        self.highlights.clear()
        self.recording = True
        self.start_time = time.time()
        
        # Create output directory
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{timestamp}_{scenario_name}"
        if test_name:
            base_name += f"_{test_name}"
        self.output_path = output_dir / f"{base_name}.{self.config.format}"
    
    def capture_frame(self, game_state: GameState, events: Optional[List[Dict]] = None) -> None:
        """
        Capture a frame from the simulation.
        
        Args:
            game_state: Current game state
            events: List of events that occurred this frame
        """
        if not self.recording or not self.config.enabled:
            return
        
        frame = Frame(
            frame_number=len(self.frames),
            simulation_time=game_state.simulation_time,
            game_state=game_state.get_state(),
            events=events or []
        )
        
        self.frames.append(frame)
        
        # Track events for highlighting
        for event in (events or []):
            self.events.append({
                **event,
                "frame": frame.frame_number,
                "time": game_state.simulation_time
            })
    
    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and generate video.
        
        Returns:
            Path to output video, or None if recording disabled
        """
        if not self.recording or not self.config.enabled:
            return None
        
        self.recording = False
        
        if not self.frames:
            return None
        
        # Generate video
        video_path = self._generate_video()
        
        return video_path
    
    def _generate_video(self) -> str:
        """Generate video from captured frames."""
        if not self.output_path:
            return ""
        
        print(f"Generating video: {self.output_path}")
        print(f"  Frames: {len(self.frames)}")
        print(f"  Resolution: {self.config.resolution}")
        print(f"  FPS: {self.config.fps}")
        
        # Create temp directory for frames
        self.temp_dir = tempfile.mkdtemp(prefix="norad_video_")
        
        # Render frames
        frame_files = []
        for i, frame in enumerate(self.frames):
            frame_file = self._render_frame(frame, i)
            if frame_file:
                frame_files.append(frame_file)
        
        # Encode video
        video_path = self._encode_video(frame_files)
        
        # Cleanup
        self._cleanup()
        
        return video_path
    
    def _render_frame(self, frame: Frame, index: int) -> Optional[str]:
        """Render a single frame to image."""
        if not HAS_MATPLOTLIB:
            return None
        
        # Calculate figure dimensions for exact pixel resolution
        width, height = self.config.resolution
        # Ensure even dimensions (required for H.264)
        width = width - (width % 2)
        height = height - (height % 2)
        
        # Use exact pixel dimensions
        dpi = 100
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        fig.set_facecolor(self.COLORS["background"])
        
        # Draw globe
        self._draw_globe(ax, frame)
        
        # Draw missiles and interceptors
        self._draw_entities(ax, frame)
        
        # Draw UI overlay
        self._draw_overlay(ax, frame)
        
        # Save frame
        frame_path = os.path.join(self.temp_dir, f"frame_{index:06d}.png")
        # Save frame with exact dimensions (no bbox_inches to preserve size)
        plt.savefig(frame_path, facecolor=self.COLORS["background"], pad_inches=0)
        plt.close(fig)
        
        return frame_path
    
    def _draw_globe(self, ax, frame: Frame) -> None:
        """Draw the globe projection with detailed continents from GeoJSON."""
        # Background
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_aspect('equal')
        ax.set_facecolor(self.COLORS["background"])
        
        # Grid lines
        if self.config.show_grid:
            for lat in range(-80, 90, 20):
                ax.axhline(lat, color=self.COLORS["grid"], alpha=0.3, linewidth=0.5)
            for lon in range(-180, 180, 30):
                ax.axvline(lon, color=self.COLORS["grid"], alpha=0.3, linewidth=0.5)
        
        # Draw world map from GeoJSON (if available)
        if self.world_map.loaded:
            self.world_map.draw(ax, land_color=self.COLORS["land"], alpha=0.7)
        else:
            # Fallback to simplified continents
            self._draw_simple_continents(ax)
        
        # Draw cities
        for city, (lat, lon) in self._cities.items():
            ax.plot(lon, lat, 'o', color=self.COLORS["city"], markersize=4, alpha=0.7)
            ax.text(lon + 2, lat + 2, city, color=self.COLORS["text"], 
                   fontsize=6, alpha=0.5)
        
        # Draw launch sites
        for site, (lat, lon) in self._launch_sites.items():
            ax.plot(lon, lat, '^', color=self.COLORS["launch_site"], 
                   markersize=5, alpha=0.7)
    
    def _draw_simple_continents(self, ax) -> None:
        """Draw simplified continent shapes as fallback."""
        # Detailed continent outlines (simplified but recognizable)
        continents = {
            "north_america": [
                (-168, 65), (-165, 70), (-160, 70), (-145, 72), (-130, 72),
                (-120, 70), (-105, 72), (-95, 75), (-80, 75), (-70, 75),
                (-60, 80), (-80, 83), (-100, 83), (-120, 80), (-140, 78),
                (-160, 75), (-168, 70),  # Arctic
                (-168, 55), (-155, 58), (-145, 60), (-130, 58), (-125, 50),
                (-124, 40), (-117, 32), (-105, 25), (-97, 25), (-90, 20),
                (-87, 15), (-85, 10), (-82, 8), (-78, 5), (-77, 8),
                (-82, 10), (-85, 15), (-82, 22), (-87, 30), (-95, 28),
                (-100, 30), (-105, 32), (-110, 35), (-118, 38), (-124, 42),
                (-128, 50), (-135, 55), (-145, 58), (-155, 58), (-168, 55)
            ],
            "south_america": [
                (-80, 10), (-75, 5), (-70, 5), (-55, 5), (-35, -5),
                (-30, -15), (-35, -25), (-45, -30), (-55, -35), (-65, -50),
                (-70, -55), (-75, -50), (-70, -45), (-68, -40), (-70, -35),
                (-75, -30), (-70, -20), (-65, -5), (-75, 0), (-80, 10)
            ],
            "europe": [
                (-10, 35), (0, 35), (10, 38), (20, 40), (30, 45), (40, 50),
                (50, 55), (60, 60), (70, 68), (65, 72), (50, 70), (30, 70),
                (20, 65), (10, 60), (0, 55), (-10, 50), (-10, 40), (-10, 35)
            ],
            "africa": [
                (-15, 35), (0, 37), (10, 35), (15, 32), (25, 30), (35, 28),
                (40, 15), (50, 10), (45, 0), (40, -5), (35, -15), (30, -30),
                (20, -35), (15, -30), (20, -25), (25, -15), (30, -5),
                (35, 5), (30, 15), (20, 20), (10, 25), (0, 25), (-10, 20),
                (-15, 25), (-15, 35)
            ],
            "asia": [
                (30, 45), (40, 45), (55, 50), (70, 55), (90, 60), (110, 65),
                (130, 70), (150, 70), (170, 68), (180, 65), (170, 60),
                (150, 55), (140, 50), (130, 45), (125, 40), (120, 30),
                (110, 22), (100, 15), (95, 8), (100, 0), (105, -5),
                (110, -5), (120, 5), (125, 10), (122, 20), (110, 25),
                (100, 30), (90, 30), (80, 25), (70, 20), (60, 25),
                (55, 30), (50, 35), (40, 38), (30, 45)
            ],
            "australia": [
                (115, -20), (120, -15), (130, -12), (140, -15), (145, -20),
                (150, -25), (153, -28), (150, -35), (145, -40), (135, -35),
                (130, -30), (120, -30), (115, -25), (115, -20)
            ],
            "greenland": [
                (-45, 60), (-35, 65), (-25, 70), (-20, 75), (-25, 80),
                (-40, 83), (-55, 82), (-65, 78), (-60, 72), (-50, 65),
                (-45, 60)
            ]
        }
        
        # Draw continents
        for continent, coords in continents.items():
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            ax.fill(lons, lats, color=self.COLORS["land"], alpha=0.7)
            ax.plot(lons, lats, color=self.COLORS["land"], alpha=0.9, linewidth=0.5)
    
    def _draw_entities(self, ax, frame: Frame) -> None:
        """Draw missiles and interceptors."""
        state = frame.game_state
        
        # Draw missile trajectories
        if self.config.show_trajectories:
            for missile_data in state.get("missiles", []):
                # Get origin and target
                origin = self._launch_sites.get(missile_data.get("origin", ""), (0, 0))
                target = self._cities.get(missile_data.get("target", ""), (0, 0))
                
                if missile_data.get("intercepted"):
                    continue
                
                # Draw trajectory line
                ax.plot([origin[1], target[1]], [origin[0], target[0]], 
                       '--', color=self.COLORS["missile_midcourse"], 
                       alpha=0.3, linewidth=1)
        
        # Draw active missiles
        for missile_data in state.get("missiles", []):
            if missile_data.get("intercepted"):
                continue
            
            # Get position from game state
            pos = missile_data.get("position", {"lat": 0, "lon": 0})
            
            # Color based on phase
            phase = missile_data.get("status", "midcourse")
            if phase == "boost":
                color = self.COLORS["missile_boost"]
                marker = 'o'
            elif phase == "terminal":
                color = self.COLORS["missile_terminal"]
                marker = 'x'
            else:
                color = self.COLORS["missile_midcourse"]
                marker = 'o'
            
            # Draw missile
            ax.plot(pos["lon"], pos["lat"], marker, color=color, 
                   markersize=8, markeredgecolor='white', markeredgewidth=1)
            
            # Label
            ax.text(pos["lon"] + 3, pos["lat"] + 3, 
                   missile_data["id"][-4:], color=color, fontsize=7)
        
        # Draw interceptors
        for interceptor_data in state.get("interceptors", []):
            # Find target missile position
            target_id = interceptor_data.get("missile_id", "")
            target_pos = None
            
            for missile_data in state.get("missiles", []):
                if missile_data.get("id") == target_id:
                    target_pos = missile_data.get("position", {"lat": 0, "lon": 0})
                    break
            
            if target_pos:
                # Draw interceptor approaching target
                ax.plot(target_pos["lon"], target_pos["lat"], '*', 
                       color=self.COLORS["interceptor"], markersize=10)
                ax.text(target_pos["lon"] - 5, target_pos["lat"] + 5,
                       interceptor_data["type"], color=self.COLORS["interceptor"],
                       fontsize=7)
        
        # Draw highlights for recent events
        if self.config.highlight_interceptions:
            for event in frame.events:
                if event.get("action") == "launch_interceptor":
                    ax.annotate('⚡', xy=(0.95, 0.95), xycoords='axes fraction',
                               fontsize=14, color=self.COLORS["highlight"],
                               ha='center', va='center')
    
    def _draw_overlay(self, ax, frame: Frame) -> None:
        """Draw UI overlay (DEFCON, stats, time)."""
        state = frame.game_state
        
        # DEFCON indicator
        if self.config.show_defcon:
            defcon = state.get("defcon", 5)
            defcon_color = self.DEFCON_COLORS.get(defcon, "#ffffff")
            
            ax.text(0.02, 0.98, f"DEFCON {defcon}", 
                   transform=ax.transAxes, fontsize=16, fontweight='bold',
                   color=defcon_color, va='top')
        
        # Stats
        if self.config.show_stats:
            stats = state.get("stats", {})
            
            info_lines = [
                f"Threats: {stats.get('threats_active', 0)}",
                f"Launched: {stats.get('missiles_launched', 0)}",
                f"Intercepted: {stats.get('missiles_intercepted', 0)}",
                f"Cities Hit: {stats.get('cities_hit', 0)}"
            ]
            
            for i, line in enumerate(info_lines):
                ax.text(0.02, 0.85 - i * 0.05, line,
                       transform=ax.transAxes, fontsize=10,
                       color=self.COLORS["text"], va='top')
        
        # Time
        sim_time = frame.simulation_time
        minutes = int(sim_time // 60)
        seconds = int(sim_time % 60)
        
        ax.text(0.98, 0.98, f"T+{minutes:02d}:{seconds:02d}",
               transform=ax.transAxes, fontsize=12,
               color=self.COLORS["text"], ha='right', va='top')
        
        # Frame number
        ax.text(0.98, 0.02, f"Frame {frame.frame_number}",
               transform=ax.transAxes, fontsize=8,
               color=self.COLORS["text"], alpha=0.5,
               ha='right', va='bottom')
        
        # Event notifications
        if frame.events:
            y_pos = 0.5
            for event in frame.events[-3:]:  # Show last 3 events
                event_text = event.get("message", str(event))
                ax.text(0.98, y_pos, event_text,
                       transform=ax.transAxes, fontsize=9,
                       color=self.COLORS["highlight"],
                       ha='right', va='center')
                y_pos -= 0.05
    
    def _encode_video(self, frame_files: List[str]) -> str:
        """Encode frames to video using ffmpeg."""
        if not frame_files:
            return ""
        
        output_file = str(self.output_path)
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-framerate", str(self.config.fps),
            "-i", os.path.join(self.temp_dir, "frame_%06d.png"),
        ]
        
        # Output format specific options
        if self.config.format == "mp4":
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium" if self.config.compression == "medium" else "fast",
                "-crf", "23" if self.config.compression == "medium" else "28",
                "-pix_fmt", "yuv420p",
            ])
        elif self.config.format == "gif":
            cmd.extend([
                "-filter_complex", "[0:v] fps=15,scale=1280:-1,split [a][b];[a] palettegen [p];[b][p] paletteuse",
            ])
        elif self.config.format == "webm":
            cmd.extend([
                "-c:v", "libvpx-vp9",
                "-crf", "30",
                "-b:v", "0",
            ])
        
        cmd.append(output_file)
        
        # Run ffmpeg
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return ""
        except subprocess.TimeoutExpired:
            print("FFmpeg timeout")
            return ""
        except Exception as e:
            print(f"Video encoding error: {e}")
            return ""
        
        return output_file
    
    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)
            self.temp_dir = None
    
    def get_summary(self) -> Dict:
        """Get recording summary."""
        return {
            "frames_captured": len(self.frames),
            "events_recorded": len(self.events),
            "duration_seconds": self.frames[-1].simulation_time if self.frames else 0,
            "output_path": str(self.output_path) if self.output_path else None,
            "config": {
                "format": self.config.format,
                "resolution": self.config.resolution,
                "fps": self.config.fps
            }
        }


class TestRecorder:
    """
    Context manager for recording test sessions.
    
    Usage:
        config = RecordingConfig()
        recorder = TestRecorder(config)
        recorder.start_recording("tutorial", "test_1")
        # Run test
        recorder.capture_frame(game_state)
        video_path = recorder.stop_recording()
    """
    
    def __init__(self, scenario_name: str = "test", test_name: str = "",
                 config: Optional[RecordingConfig] = None):
        self.recorder = VideoRecorder(config)
        self.scenario_name = scenario_name
        self.test_name = test_name
    
    def __enter__(self):
        self.recorder.start_recording(self.scenario_name, self.test_name)
        return self.recorder
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        video_path = self.recorder.stop_recording()
        if video_path:
            print(f"Video saved: {video_path}")
        return False  # Don't suppress exceptions