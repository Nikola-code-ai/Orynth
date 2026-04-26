"""Planned ArduPilot adapter boundary.

This module intentionally stops at the interface definition for now.
ArduPilot support in this repository will target AP_DDS first and MAVROS only
as a fallback for features that are not yet exposed cleanly through AP_DDS.
"""

from __future__ import annotations

from .swarm_api import (
    FollowReferenceRequest,
    LandRequest,
    MotionTarget,
    PlatformProfile,
    TakeoffRequest,
)
from .vehicle_adapter import VehicleAdapter


class ArduPilotAdapter(VehicleAdapter):
    """Placeholder for the future AP_DDS-backed vehicle adapter."""

    def __init__(self, vehicle_id: str, profile: PlatformProfile = PlatformProfile.ARDUPILOT_SITL):
        self._vehicle_id = vehicle_id
        self._profile = profile

    @property
    def vehicle_id(self) -> str:
        return self._vehicle_id

    @property
    def platform_profile(self) -> PlatformProfile:
        return self._profile

    def arm(self) -> bool:
        raise NotImplementedError('ArduPilotAdapter.arm() is not implemented yet.')

    def enable_external_control(self) -> bool:
        raise NotImplementedError('ArduPilotAdapter.enable_external_control() is not implemented yet.')

    def takeoff(self, request: TakeoffRequest) -> bool:
        raise NotImplementedError('ArduPilotAdapter.takeoff() is not implemented yet.')

    def go_to(self, target: MotionTarget) -> bool:
        raise NotImplementedError('ArduPilotAdapter.go_to() is not implemented yet.')

    def hold_reference(self, request: FollowReferenceRequest) -> bool:
        raise NotImplementedError('ArduPilotAdapter.hold_reference() is not implemented yet.')

    def land(self, request: LandRequest) -> bool:
        raise NotImplementedError('ArduPilotAdapter.land() is not implemented yet.')

    def close(self) -> None:
        return None
