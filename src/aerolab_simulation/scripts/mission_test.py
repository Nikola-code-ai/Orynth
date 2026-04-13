#!/usr/bin/env python3
"""
mission_test.py — Phase 1 swarm mission validation script.

Commands drone0 through a takeoff → waypoint → land sequence and verifies
that drones 1-4 hold their formation offsets at each stage.

Prerequisites:
  1. swarm_bringup_launch.py must be running (Gazebo + all 5 drone stacks)
  2. flock_orchestrator must have taken off all drones and activated formation
     (run flock_orchestrator first OR launch with use_flock_orchestrator:=true)

The script will wait up to 15 s for drone0 to be airborne before proceeding.
If flock_orchestrator is not running, the formation checks will FAIL (expected).

Run (inside container, workspace sourced):
  python3 /root/aerolab_ws/src/aerolab_simulation/scripts/mission_test.py

Formation offsets match flock_orchestrator.py (must stay in sync):
  drone1: (+3,  0, 0) — Front
  drone2: ( 0, +3, 0) — Left
  drone3: ( 0, -3, 0) — Right
  drone4: (-3,  0, 0) — Rear
"""

import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

try:
    from as2_python_api.drone_interface import DroneInterface
except ImportError:
    print('[mission_test] ERROR: as2_python_api not found.')
    print('  Verify with: ros2 pkg list | grep as2_python_api')
    sys.exit(1)

# ── Formation geometry (must match flock_orchestrator.py) ──────────────────────
FORMATION_OFFSETS = {
    'drone1': (3.0,  0.0),   # Front
    'drone2': (0.0,  3.0),   # Left
    'drone3': (0.0, -3.0),   # Right
    'drone4': (-3.0, 0.0),   # Rear
}
FORMATION_TOLERANCE_M = 0.5   # max acceptable horizontal drift

# ── Mission parameters ─────────────────────────────────────────────────────────
TAKEOFF_HEIGHT_M  = 2.0
TAKEOFF_SPEED     = 0.5
WAYPOINT          = [5.0, 0.0, 2.0]
CRUISE_SPEED      = 1.0
LAND_SPEED        = 0.3
AIRBORNE_WAIT_S   = 15.0   # how long to wait for drone0 to be airborne
AIRBORNE_HEIGHT_M = 0.5    # drone0 height threshold to consider it airborne


class FormationVerifier(Node):
    """Lightweight subscriber node that tracks all 5 drone poses."""

    def __init__(self):
        super().__init__('formation_verifier')
        self.poses = {}
        for ns in ['drone0', 'drone1', 'drone2', 'drone3', 'drone4']:
            self.create_subscription(
                PoseStamped,
                f'/{ns}/self_localization/pose',
                lambda msg, name=ns: self.poses.update({name: msg.pose}),
                10
            )

    def spin_for(self, seconds: float):
        deadline = time.time() + seconds
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)

    def get_pose(self, name: str):
        return self.poses.get(name)

    def wait_for_airborne(self, timeout: float) -> bool:
        """Return True when drone0 is above AIRBORNE_HEIGHT_M."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.spin_for(0.2)
            pose = self.get_pose('drone0')
            if pose and pose.position.z >= AIRBORNE_HEIGHT_M:
                return True
        return False


def check_formation(verifier: FormationVerifier, stage: str) -> bool:
    verifier.spin_for(1.0)

    leader_pose = verifier.get_pose('drone0')
    if leader_pose is None:
        print(f'[{stage}] FAIL: No pose received for drone0.')
        return False

    lx = leader_pose.position.x
    ly = leader_pose.position.y

    all_pass = True
    for drone, (dx, dy) in FORMATION_OFFSETS.items():
        expected_x = lx + dx
        expected_y = ly + dy
        follower   = verifier.get_pose(drone)

        if follower is None:
            print(f'[{stage}] {drone}: FAIL — no pose received')
            all_pass = False
            continue

        dist = ((follower.position.x - expected_x) ** 2 +
                (follower.position.y - expected_y) ** 2) ** 0.5

        if dist <= FORMATION_TOLERANCE_M:
            print(f'[{stage}] {drone}: PASS (drift={dist:.2f}m)')
        else:
            print(f'[{stage}] {drone}: FAIL (drift={dist:.2f}m, limit={FORMATION_TOLERANCE_M}m)')
            all_pass = False

    return all_pass


def main():
    rclpy.init()
    verifier = FormationVerifier()

    drone0 = DroneInterface(
        drone_id='drone0',
        use_sim_time=True,
        verbose=True
    )

    print('\n[mission_test] ═══ Phase 1 Mission Test ═══')
    print(f'[mission_test] Waypoint: {WAYPOINT}')
    print(f'[mission_test] Formation tolerance: {FORMATION_TOLERANCE_M}m\n')

    # ── Step 1: Ensure drone0 is airborne ─────────────────────────────────────
    # If flock_orchestrator is running, drones are already in the air.
    # If not, attempt takeoff ourselves.
    print('[mission_test] Step 1: Checking drone0 altitude...')
    if verifier.wait_for_airborne(timeout=3.0):
        print(f'[mission_test] drone0 already airborne (z >= {AIRBORNE_HEIGHT_M}m). Skipping takeoff.')
    else:
        print(f'[mission_test] drone0 not airborne — attempting takeoff to {TAKEOFF_HEIGHT_M}m...')
        result = drone0.takeoff(height=TAKEOFF_HEIGHT_M, speed=TAKEOFF_SPEED)
        if not result:
            print('[mission_test] FAIL: TakeOff rejected or timed out.')
            print('  Are behavior action servers running? (drone_stack_launch.py)')
            drone0.destroy_node()
            verifier.destroy_node()
            rclpy.shutdown()
            sys.exit(1)
        print('[mission_test] TakeOff complete.')

    print('[mission_test] Waiting 3s for formation to stabilise...')
    time.sleep(3.0)

    # ── Step 2: Formation check at hover ───────────────────────────────────────
    print('\n[mission_test] Step 2: Formation check at hover')
    hover_pass = check_formation(verifier, 'HOVER')
    print(f'[mission_test] Hover formation: {"PASS" if hover_pass else "FAIL"}')

    # ── Step 3: Fly to waypoint ────────────────────────────────────────────────
    print(f'\n[mission_test] Step 3: GoTo {WAYPOINT} at {CRUISE_SPEED}m/s')
    result = drone0.go_to.go_to_point(
        point=WAYPOINT,
        speed=CRUISE_SPEED,
    )
    if not result:
        print('[mission_test] FAIL: GoTo rejected or timed out.')
        drone0.land(speed=LAND_SPEED)
        drone0.destroy_node()
        verifier.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    print('[mission_test] Waypoint reached. Waiting 3s for formation to catch up...')
    time.sleep(3.0)

    # ── Step 4: Formation check at waypoint ────────────────────────────────────
    print('\n[mission_test] Step 4: Formation check at waypoint')
    waypoint_pass = check_formation(verifier, 'WAYPOINT')
    print(f'[mission_test] Waypoint formation: {"PASS" if waypoint_pass else "FAIL"}')

    # ── Step 5: Land drone0 ────────────────────────────────────────────────────
    # Drones 1-4 will remain hovering at their last formation positions after
    # drone0 lands (follow_reference keeps them at the last known transform).
    print('\n[mission_test] Step 5: Landing drone0...')
    drone0.land(speed=LAND_SPEED)

    # ── Summary ────────────────────────────────────────────────────────────────
    print('\n[mission_test] ═══ Results ═══')
    print(f'  Hover formation:    {"PASS" if hover_pass else "FAIL"}')
    print(f'  Waypoint formation: {"PASS" if waypoint_pass else "FAIL"}')
    overall = hover_pass and waypoint_pass
    print(f'  Overall:            {"PASS" if overall else "FAIL"}\n')

    drone0.destroy_node()
    verifier.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if overall else 1)


if __name__ == '__main__':
    main()
