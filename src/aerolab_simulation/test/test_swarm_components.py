from math import pi

import pytest

from aerolab_simulation.formation import DIAMOND_FORMATION, FOLLOWER_IDS, LEADER_ID
from aerolab_simulation.swarm_api import (
    AutonomyMode,
    FollowReferenceRequest,
    MotionTarget,
    PlatformProfile,
    SwarmStatusSnapshot,
    TakeoffRequest,
)


def test_diamond_formation_offsets_are_stable():
    assert DIAMOND_FORMATION.name == 'diamond'
    assert DIAMOND_FORMATION.leader_id == LEADER_ID
    assert tuple(DIAMOND_FORMATION.offsets.keys()) == FOLLOWER_IDS


def test_expected_position_uses_relative_offsets():
    expected = DIAMOND_FORMATION.expected_position('drone2', (10.0, -2.0, 3.0))
    assert expected == (10.0, 1.0, 3.0)


def test_expected_position_rotates_with_leader_yaw():
    expected = DIAMOND_FORMATION.expected_position(
        'drone1',
        (0.0, 0.0, 2.0),
        leader_yaw_rad=pi / 2,
    )
    assert expected == pytest.approx((0.0, 3.0, 2.0))


def test_horizontal_drift_is_zero_when_follower_matches_slot():
    drift = DIAMOND_FORMATION.horizontal_drift(
        'drone4',
        leader_xy=(4.0, 5.0),
        follower_xy=(1.0, 5.0),
    )
    assert drift == 0.0


def test_horizontal_drift_respects_leader_yaw():
    drift = DIAMOND_FORMATION.horizontal_drift(
        'drone3',
        leader_xy=(2.0, -1.0),
        follower_xy=(5.0, -1.0),
        leader_yaw_rad=pi / 2,
    )
    assert drift == pytest.approx(0.0)


def test_shared_swarm_types_capture_platform_boundary():
    takeoff = TakeoffRequest(height_m=2.0, speed_mps=0.5)
    target = MotionTarget(point=(1.0, 2.0, 3.0), speed_mps=1.2, frame_id='earth')
    follow = FollowReferenceRequest(
        x=3.0,
        y=0.0,
        z=0.0,
        frame_id='drone0/base_link',
        speed_x_mps=2.0,
        speed_y_mps=2.0,
        speed_z_mps=2.0,
    )

    snapshot = SwarmStatusSnapshot(
        platform_profile=PlatformProfile.ARDUPILOT_SITL,
        autonomy_mode=AutonomyMode.FORMATION_HOLD,
        leader_id=LEADER_ID,
        formation_name=DIAMOND_FORMATION.name,
        active_vehicles=(LEADER_ID, *FOLLOWER_IDS),
    )

    assert takeoff.height_m == 2.0
    assert target.frame_id == 'earth'
    assert follow.frame_id == 'drone0/base_link'
    assert snapshot.platform_profile is PlatformProfile.ARDUPILOT_SITL
