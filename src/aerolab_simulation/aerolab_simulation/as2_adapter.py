"""Aerostack2-backed vehicle adapter."""

from __future__ import annotations

from .swarm_api import (
    FollowReferenceRequest,
    LandRequest,
    MotionTarget,
    PlatformProfile,
    TakeoffRequest,
)
from .vehicle_adapter import VehicleAdapter

try:
    from as2_python_api.drone_interface import DroneInterface
    from as2_python_api.modules.follow_reference_module import FollowReferenceModule
except ImportError:  # pragma: no cover - exercised only in ROS runtime.
    DroneInterface = None
    FollowReferenceModule = None


class As2VehicleAdapter(VehicleAdapter):
    """Wrap the Aerostack2 Python API behind the shared adapter contract."""

    def __init__(self, vehicle_id: str, use_sim_time: bool = True, verbose: bool = True):
        if DroneInterface is None:
            raise ImportError(
                'as2_python_api is not available. Source the Aerostack2 workspace before '
                'using As2VehicleAdapter.'
            )
        self._vehicle_id = vehicle_id
        self._drone = DroneInterface(
            drone_id=vehicle_id,
            use_sim_time=use_sim_time,
            verbose=verbose,
        )

    @property
    def vehicle_id(self) -> str:
        return self._vehicle_id

    @property
    def platform_profile(self) -> PlatformProfile:
        return PlatformProfile.AEROSTACK2_SIM

    @property
    def node(self):
        return self._drone

    def arm(self) -> bool:
        return self._drone.arm()

    def enable_external_control(self) -> bool:
        return self._drone.offboard()

    def takeoff(self, request: TakeoffRequest) -> bool:
        return self._drone.takeoff(height=request.height_m, speed=request.speed_mps)

    def go_to(self, target: MotionTarget) -> bool:
        return self._drone.go_to.go_to_point(
            point=list(target.point),
            speed=target.speed_mps,
        )

    def hold_reference(self, request: FollowReferenceRequest) -> bool:
        if not hasattr(self._drone, 'follow_reference'):
            if FollowReferenceModule is None:
                raise ImportError('FollowReferenceModule is not available in this environment.')
            self._drone.follow_reference = FollowReferenceModule(drone=self._drone)

        return self._drone.follow_reference.follow_reference(
            x=request.x,
            y=request.y,
            z=request.z,
            frame_id=request.frame_id,
            speed_x=request.speed_x_mps,
            speed_y=request.speed_y_mps,
            speed_z=request.speed_z_mps,
        )

    def land(self, request: LandRequest) -> bool:
        return self._drone.land(speed=request.speed_mps)

    def close(self) -> None:
        self._drone.destroy_node()
