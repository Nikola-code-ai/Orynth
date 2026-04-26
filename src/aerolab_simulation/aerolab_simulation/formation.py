"""Shared swarm geometry helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, sin
from typing import Mapping

LEADER_ID = 'drone0'
FOLLOWER_IDS = ('drone1', 'drone2', 'drone3', 'drone4')


@dataclass(frozen=True)
class FormationLayout:
    """Relative follower offsets from the leader frame."""

    name: str
    leader_id: str
    offsets: Mapping[str, tuple[float, float, float]]

    def expected_position(
        self,
        follower_id: str,
        leader_xyz: tuple[float, float, float],
        leader_yaw_rad: float = 0.0,
    ) -> tuple[float, float, float]:
        dx, dy, dz = self.offsets[follower_id]
        lx, ly, lz = leader_xyz
        world_dx = dx * cos(leader_yaw_rad) - dy * sin(leader_yaw_rad)
        world_dy = dx * sin(leader_yaw_rad) + dy * cos(leader_yaw_rad)
        return lx + world_dx, ly + world_dy, lz + dz

    def horizontal_drift(
        self,
        follower_id: str,
        leader_xy: tuple[float, float],
        follower_xy: tuple[float, float],
        leader_yaw_rad: float = 0.0,
    ) -> float:
        expected_x, expected_y, _ = self.expected_position(
            follower_id,
            (leader_xy[0], leader_xy[1], 0.0),
            leader_yaw_rad=leader_yaw_rad,
        )
        return hypot(follower_xy[0] - expected_x, follower_xy[1] - expected_y)


DIAMOND_FORMATION = FormationLayout(
    name='diamond',
    leader_id=LEADER_ID,
    offsets={
        'drone1': (3.0, 0.0, 0.0),
        'drone2': (0.0, 3.0, 0.0),
        'drone3': (0.0, -3.0, 0.0),
        'drone4': (-3.0, 0.0, 0.0),
    },
)
