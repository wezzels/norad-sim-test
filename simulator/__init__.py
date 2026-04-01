"""NORAD War Simulator - Human Emulation Test Suite

A Python-based simulation that plays NORAD War Simulator like a human would.
"""

__version__ = "0.2.0"
__author__ = "Lucky (OpenClaw Agent)"

from .game_state import GameState
from .ballistics import Ballistics
from .defense import DefenseManager
from .detection import DetectionManager
from .scenarios import ScenarioLoader
from .human_player import HumanPlayer
from .video_recorder import VideoRecorder, RecordingConfig, TestRecorder

__all__ = [
    "GameState",
    "Ballistics", 
    "DefenseManager",
    "DetectionManager",
    "ScenarioLoader",
    "HumanPlayer",
    "VideoRecorder",
    "RecordingConfig",
    "TestRecorder",
]