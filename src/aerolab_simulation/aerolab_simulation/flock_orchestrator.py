#!/usr/bin/env python3
"""
flock_orchestrator.py — AeroLab swarm formation controller.

Takes off all 5 drones, then puts drones 1-4 into follow_reference mode
so they maintain a diamond formation around drone0 (the mothership).

Formation (relative to drone0/base_link, FLU frame):
    drone1: (+3,  0,  0) — Front
    drone2: ( 0, +3,  0) — Left
    drone3: ( 0, -3,  0) — Right
    drone4: (-3,  0,  0) — Rear

After formation is established:
  - Drone0 can be flown with keyboard_teleoperation and drones 1-4 follow.
  - Or the mission_test.py script can command drone0 autonomously.

Prerequisites:
  - swarm_bringup_launch.py must be running (Gazebo + all 5 drone stacks)
  - The follow_reference_behavior_node must be running per drone
    (it is launched by drone_stack_launch.py — no extra setup needed)

Correct AS2 approach used here:
  - DroneInterface.takeoff() calls the TakeOff action server
  - FollowReferenceModule calls the FollowReference action server on each
    follower drone with drone0/base_link as the reference TF frame
  - The follow_reference behavior runs continuously: as drone0 moves, drones
    1-4 update their targets via TF lookup in real time
"""

import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor

try:
    from as2_python_api.drone_interface import DroneInterface
    from as2_python_api.modules.follow_reference_module import FollowReferenceModule
except ImportError as e:
    raise SystemExit(
        f'[flock_orchestrator] Import error: {e}\n'
        '  Ensure the workspace is sourced: source install/setup.bash'
    )

# ── Formation geometry ─────────────────────────────────────────────────────────
# Offsets relative to drone0/base_link (FLU: x=forward, y=left, z=up)
FORMATION = {
    'drone1': (3.0,  0.0, 0.0),   # Front
    'drone2': (0.0,  3.0, 0.0),   # Left
    'drone3': (0.0, -3.0, 0.0),   # Right
    'drone4': (-3.0, 0.0, 0.0),   # Rear
}

# The TF frame that followers track.
# AS2 state estimator with ground_truth plugin publishes:
#   earth → droneN/map → droneN/odom → droneN/base_link
MOTHERSHIP_FRAME = 'drone0/base_link'

# ── Mission parameters ─────────────────────────────────────────────────────────
TAKEOFF_HEIGHT = 2.0   # metres
TAKEOFF_SPEED  = 0.5   # m/s
FOLLOW_SPEED   = 2.0   # m/s per axis for formation tracking


def _takeoff_worker(name: str, drone: DroneInterface, results: dict) -> None:
    """
    Thread worker: arm, go offboard, then take off one drone (blocking).

    AS2 TakeoffBehavior rejects goals when the platform is DISARMED or not in
    OFFBOARD control mode, so we must transition the platform through both
    before issuing the takeoff action.
    """
    print(f'[flock_orchestrator] {name}: arming...')
    if not drone.arm():
        print(f'[flock_orchestrator] {name}: ARM FAILED.')
        results[name] = False
        return
    print(f'[flock_orchestrator] {name}: enabling offboard mode...')
    if not drone.offboard():
        print(f'[flock_orchestrator] {name}: OFFBOARD FAILED.')
        results[name] = False
        return
    print(f'[flock_orchestrator] {name}: taking off to {TAKEOFF_HEIGHT} m...')
    ok = drone.takeoff(height=TAKEOFF_HEIGHT, speed=TAKEOFF_SPEED)
    results[name] = ok
    status = 'OK' if ok else 'FAILED'
    print(f'[flock_orchestrator] {name}: takeoff {status}.')


def takeoff_all(drones: dict) -> bool:
    """Take off all drones simultaneously; return True if all succeeded."""
    results = {}
    threads = [
        threading.Thread(target=_takeoff_worker, args=(name, drone, results), daemon=True)
        for name, drone in drones.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30.0)
    return all(results.get(n, False) for n in drones)


def start_formation(followers: dict) -> bool:
    """
    Activate follow_reference on drones 1-4.

    Each follower drone receives a non-blocking FollowReference goal with:
      target_pose.header.frame_id = 'drone0/base_link'
      target_pose.point           = formation offset
      max_speed_x/y/z             = FOLLOW_SPEED

    The behavior then runs continuously, re-computing the target position via
    TF at each control cycle as drone0 moves.
    """
    success = True
    for name, (ox, oy, oz) in FORMATION.items():
        drone = followers[name]
        print(
            f'[flock_orchestrator] {name}: follow_reference '
            f'offset=({ox:+.1f}, {oy:+.1f}, {oz:+.1f}) m '
            f'frame={MOTHERSHIP_FRAME}'
        )
        ok = drone.follow_reference.follow_reference(
            x=ox, y=oy, z=oz,
            frame_id=MOTHERSHIP_FRAME,
            speed_x=FOLLOW_SPEED,
            speed_y=FOLLOW_SPEED,
            speed_z=FOLLOW_SPEED,
        )
        status = 'ACTIVE' if ok else 'REJECTED'
        print(f'[flock_orchestrator] {name}: follow_reference {status}.')
        success = success and ok
    return success


def _wait_for_action(drones: dict, action_cls, action_name: str,
                     timeout: float = 45.0) -> bool:
    """
    Wait until every drone has `action_name` available on its action server.

    Polls a temporary ActionClient per drone — avoids relying on AS2 internal
    attribute names and does not require the DroneInterface to have its module
    attached yet.
    """
    from rclpy.action import ActionClient

    deadline = time.monotonic() + timeout
    pending = set(drones.keys())
    tmp_clients = {}

    print(f'[flock_orchestrator] Waiting for {action_name} on {sorted(drones)} '
          f'(up to {timeout:.0f}s)...')

    for name, drone in drones.items():
        tmp_clients[name] = ActionClient(drone, action_cls, f'/{name}/{action_name}')

    try:
        while pending and time.monotonic() < deadline:
            for name in list(pending):
                if tmp_clients[name].wait_for_server(timeout_sec=0.0):
                    print(f'[flock_orchestrator] {name}: {action_name} READY')
                    pending.discard(name)
            if pending:
                time.sleep(0.5)
    finally:
        for c in tmp_clients.values():
            c.destroy()

    if pending:
        print(f'[flock_orchestrator] TIMEOUT — {action_name} not ready: {sorted(pending)}')
        return False
    return True


def _wait_for_action_servers(drones: dict, followers: dict, timeout: float = 45.0) -> bool:
    """
    Wait for Takeoff on all drones AND FollowReference on followers.

    Why both: BehaviorHandler.__init__ has a 1-second discovery timeout and
    swallows BehaviorNotAvailable into a warn log. Constructing
    FollowReferenceModule before the server is discoverable leaves it silently
    non-functional on the affected drones, so we must pre-verify discovery for
    FollowReferenceBehavior before the modules are created.
    """
    from as2_msgs.action import Takeoff as TakeoffAction
    from as2_msgs.action import FollowReference as FollowReferenceAction

    if not _wait_for_action(drones, TakeoffAction, 'TakeoffBehavior', timeout):
        return False
    if not _wait_for_action(followers, FollowReferenceAction,
                            'FollowReferenceBehavior', timeout):
        return False
    return True


def main(args=None) -> None:
    rclpy.init(args=args)

    print('[flock_orchestrator] Initialising drone interfaces...')
    all_names = ['drone0', 'drone1', 'drone2', 'drone3', 'drone4']
    follower_names = ['drone1', 'drone2', 'drone3', 'drone4']

    drones = {
        name: DroneInterface(drone_id=name, use_sim_time=True, verbose=True)
        for name in all_names
    }
    followers = {n: drones[n] for n in follower_names}

    print('[flock_orchestrator] All interfaces created. Checking action server readiness...')

    # Both Takeoff AND FollowReference must be discoverable BEFORE the
    # FollowReferenceModule is constructed — see _wait_for_action_servers docstring.
    servers_ready = _wait_for_action_servers(drones, followers, timeout=45.0)
    if not servers_ready:
        print('[flock_orchestrator] Action servers never became ready — is swarm_bringup_launch.py running?')
        for d in drones.values():
            d.destroy_node()
        rclpy.shutdown()
        return

    print('[flock_orchestrator] All action servers ready. Attaching FollowReference modules...')
    for name in follower_names:
        drones[name].follow_reference = FollowReferenceModule(drone=drones[name])

    # ── Step 1: Simultaneous takeoff ───────────────────────────────────────────
    print(f'\n[flock_orchestrator] === Step 1: Takeoff (all {len(all_names)} drones) ===')
    ok = takeoff_all(drones)
    if not ok:
        print('[flock_orchestrator] One or more takeoffs FAILED — aborting.')
        print('[flock_orchestrator] Likely cause: TF chain (earth→base_link) not connected.')
        print('[flock_orchestrator] Check: ros2 run tf2_ros tf2_echo earth drone0/base_link')
        for d in drones.values():
            d.destroy_node()
        rclpy.shutdown()
        return

    print('[flock_orchestrator] All drones airborne. Stabilising for 3 s...')
    time.sleep(3.0)

    # ── Step 2: Diamond formation hold ────────────────────────────────────────
    print('\n[flock_orchestrator] === Step 2: Diamond formation hold ===')
    ok = start_formation(followers)

    if ok:
        print(
            '\n[flock_orchestrator] Diamond formation ACTIVE.\n'
            '  Drone0 is the leader — fly it with keyboard_teleoperation.\n'
            '  Drones 1-4 will follow automatically.\n'
            '  Press Ctrl-C to shut down.\n'
        )
    else:
        print(
            '\n[flock_orchestrator] WARNING: some follow_reference goals REJECTED.\n'
            '  Check follow_reference_behavior_node is running per drone.\n'
            '  Check TF chain: ros2 run tf2_ros tf2_echo earth drone1/base_link\n'
        )

    try:
        while rclpy.ok():
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        print('\n[flock_orchestrator] Shutting down...')
        for d in drones.values():
            d.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
