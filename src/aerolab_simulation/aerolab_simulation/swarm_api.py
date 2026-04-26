"""Shared control-layer types for swarm orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlatformProfile(str, Enum):
    AEROSTACK2_SIM = 'aerostack2_sim'
    ARDUPILOT_SITL = 'ardupilot_sitl'
    ARDUPILOT_REAL = 'ardupilot_real'


class AutonomyMode(str, Enum):
    MANUAL_LEADER = 'manual_leader'
    FORMATION_HOLD = 'formation_hold'
    FORMATION_MISSION = 'formation_mission'
    SAFETY_ABORT = 'safety_abort'


@dataclass(frozen=True)
class TakeoffRequest:
    height_m: float
    speed_mps: float


@dataclass(frozen=True)
class LandRequest:
    speed_mps: float


@dataclass(frozen=True)
class MotionTarget:
    point: tuple[float, float, float]
    speed_mps: float
    frame_id: str = 'earth'


@dataclass(frozen=True)
class FollowReferenceRequest:
    x: float
    y: float
    z: float
    frame_id: str
    speed_x_mps: float
    speed_y_mps: float
    speed_z_mps: float


@dataclass(frozen=True)
class VehicleHealth:
    vehicle_id: str
    connected: bool
    armed: bool
    external_control: bool


@dataclass(frozen=True)
class SwarmStatusSnapshot:
    platform_profile: PlatformProfile
    autonomy_mode: AutonomyMode
    leader_id: str
    formation_name: str
    active_vehicles: tuple[str, ...]

