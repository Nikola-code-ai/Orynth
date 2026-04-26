# AeroLab Simulation Development Guide

A technical reference for teammates working inside the AeroLab swarm simulation.

> This guide covers the current `Aerostack2 + Gazebo Fortress` simulation path
> only. It does not describe the planned ArduPilot SITL or hardware bringup.
> See [System Architecture](system_architecture.md) for the control-stack split.

---

## 1. Overview

The simulation runs a 5-drone swarm inside Ignition Gazebo Fortress, orchestrated by Aerostack2 over ROS 2 Humble. All communication uses CycloneDDS (`rmw_cyclonedds_cpp`). The entire stack runs inside the `aerolab_stack` Docker image, which extends `aerostack2/nightly-humble`.

Two operating modes are supported:

| Mode | Description |
|---|---|
| **Teleoperation** | Fly drone0 manually with a keyboard GUI. Drones 1–4 follow in diamond formation. |
| **Automated** | All 5 drones take off and hold diamond formation automatically. Attach keyboard teleop separately if needed. |

---

## 2. Container Setup

### Start the dev container (every session)

```bash
cd aerolab_ws/
xhost +local:root          # one-time per reboot — allows Gazebo GUI on host X11
docker compose run --rm aerolab
```

You are now inside the container at `/root/aerolab_ws`.

### Build the workspace (inside container)

Only required when you add a package, change `package.xml`, `setup.py`, or `setup.cfg`. Normal Python edits are reflected immediately via the volume mount.

```bash
colcon build
source install/setup.bash
```

### Opening additional terminals

The entrypoint writes all workspace sources to `~/.bashrc` on first run, so `docker exec` shells are fully configured automatically:

```bash
docker exec -it $(docker ps --filter ancestor=aerolab_stack --format '{{.Names}}' | head -1) bash
```

That's it — no manual `source` commands needed.

---

## 3. Node Architecture

Each drone runs under its own namespace (`/drone0` through `/drone4`). The full per-drone stack is:

```
Gazebo physics
    ↕  (ros_gz_bridge nodes — CRITICAL layer)
drone_bridges          ← ground_truth_bridge (pose+twist), cmd_vel bridge, arm bridge, IMU bridge
    ↕
as2_platform_gazebo    ← translates actuator commands → Gazebo, exposes sensors
as2_state_estimator    ← reads ground_truth bridge → publishes pose + TF
as2_motion_controller  ← PID: converts motion references → actuator commands
as2_behaviors_motion   ← action servers: TakeOff, GoTo, Land, FollowPath, FollowReference
```

### Drone Bridges

`as2_gazebo_assets/launch/drone_bridges.py` must be launched per drone. It creates the `ros_gz_bridge` nodes that connect Gazebo topics to ROS 2:

- `ground_truth_bridge` — Gazebo pose + twist → `/{namespace}/self_localization/pose` and `.../twist`
- `cmd_vel` + `arm` parameter bridges — ROS 2 commands → Gazebo actuators
- IMU bridge — Gazebo IMU → `/{namespace}/sensor_measurements/imu`

**Without these bridges the platform node is deaf and mute to Gazebo.** They are launched automatically by `drone_stack_launch.py`.

### TF Frame Hierarchy

```
earth  (global, not namespaced)
  └── droneN/map
        └── droneN/odom
              └── droneN/base_link
```

The `follow_reference_behavior` tracks `drone0/base_link` — drone0's body frame in the `earth` tree. As drone0 moves, TF updates propagate to all followers on every control cycle.

### Platform Node Parameters

The `as2_platform_gazebo_node` requires three topic parameters with no defaults — these must match the bridge ros_topic names:

```
cmd_vel_topic: /gz/{namespace}/cmd_vel
arm_topic:     /gz/{namespace}/arm
acro_topic:    /gz/{namespace}/acro
```

These are set via `OpaqueFunction` in `drone_stack_launch.py` so the namespace is resolved as a Python string at launch time.

---

## 4. Configuration Files

All YAML config lives in `src/aerolab_simulation/config/`:

| File | Purpose |
|---|---|
| `platform_gz.yaml` | Physics properties, control_modes_file path |
| `state_estimator.yaml` | Frame config — `global_ref_frame: "earth"` (not `earth_frame`) |
| `behaviors.yaml` | Default thresholds, speeds, heights for takeoff/goto/land/follow |

`src/aerolab_simulation/resource/swarm_config.json` defines the 5 drones (model type, spawn positions). Parsed by `as2_gazebo_assets`.

---

## 5. Launch Files

| File | Purpose |
|---|---|
| `swarm_bringup_launch.py` | Master launch: Gazebo world → 5 drone stacks |
| `swarm_gazebo_launch.py` | Gazebo world + model spawning only |
| `drone_stack_launch.py` | Per-drone: bridges + platform + estimator + controller + behaviors |
| `teleop_launch.py` | Keyboard teleoperation GUI for drone0 (wraps `as2_keyboard_teleoperation`) |

### swarm_bringup_launch.py arguments

```
rmw  [string, default: 'cyclonedds']
    'cyclonedds' → CycloneDDS (default, recommended)
    'zenoh'      → Zenoh with router, session config, and tf_static_bridge

use_flock_orchestrator  [bool, default: false]
    true  → launches flock_orchestrator node after all stacks are ready
    false → stacks only; attach flock_orchestrator and teleop manually
```

### Startup timing

**CycloneDDS (default):**
- t=0s: Gazebo world launches immediately
- t=6s: Drone stacks launch
- t=10s: Orchestrator (if enabled)

**Zenoh:**
- t=0s: Zenoh router starts (IPv4 on 0.0.0.0:7447)
- t=3s: Gazebo world launches
- t=11s: tf_static_bridge (transient_local workaround)
- t=12s: Drone stacks launch
- t=16s: Orchestrator (if enabled)

Wait for `TakeoffBehavior action server ready` for all 5 drones before running teleop or orchestrator separately.

---

## 6. Running the Simulation

### Mode A — Teleoperation (manual control of drone0, formation follows)

**Terminal 1** — Start the full stack:
```bash
ros2 launch aerolab_simulation swarm_bringup_launch.py
```

Wait ~15 seconds until all 5 `TakeoffBehavior action server ready` lines appear.

**Terminal 2** — Take off all drones and activate diamond formation:
```bash
ros2 run aerolab_simulation flock_orchestrator
```

Wait for: `Diamond formation ACTIVE. Drone0 is the leader.`

**Terminal 3** — Open keyboard teleoperation:
```bash
ros2 launch aerolab_simulation teleop_launch.py
```

A GUI window opens. Drones 1–4 track drone0 in real time via TF.

---

### Mode B — Automated formation (one-command bringup)

**Terminal 1:**
```bash
ros2 launch aerolab_simulation swarm_bringup_launch.py use_flock_orchestrator:=true
```

All 5 drones take off and enter diamond formation automatically.

**Terminal 2 (optional)** — Attach keyboard teleop:
```bash
ros2 launch aerolab_simulation teleop_launch.py
```

---

## 7. Formation Layout

Diamond offsets from `drone0/base_link`:

```
         drone1 (+3 m forward)
               ↑
drone2 (+3 m left) ← drone0 → drone3 (−3 m left)
               ↓
         drone4 (−3 m forward)
```

Formation is implemented via `FollowReferenceBehavior` action servers on drones 1–4. The `flock_orchestrator` node calls `DroneInterface.follow_reference.follow_reference(x, y, z, frame_id="drone0/base_link")` on each follower — the behavior runs continuously, re-computing via TF on every control cycle. No polling loop is required.

---

## 8. Phase 1 Validation

Run after `flock_orchestrator` has established formation:

```bash
python3 /root/aerolab_ws/src/aerolab_simulation/scripts/mission_test.py
```

Commands drone0 through a waypoint sequence and checks that drones 1–4 hold their formation offsets at each stage. Prints `PASS`/`FAIL` per drone per waypoint.

> **Note:** If the orchestrator is already running, the script detects drone0 is airborne and skips its own takeoff sequence.

---

## 9. Computer Vision (Phase 4 — Planned)

The Docker image includes `opencv-python-headless` and `ultralytics`. The
integration path when Phase 4 begins:

1. Add a camera plugin to the Gazebo drone model in `swarm_config.json` — standard `/image_raw` topics will be published.
2. Write a perception node using YOLO to detect targets and publish offsets.
3. Pipe those offsets into `follow_reference_behavior` (already deployed on each drone) to have followers track moving objects in real time.

---

## 10. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Drones don't move after takeoff | Bridges not started | Verify `drone_stack_launch.py` includes `drone_bridges.py` include |
| State estimator TF errors | Wrong YAML key | `state_estimator.yaml` must use `global_ref_frame: "earth"` |
| `follow_reference` action not found | FollowReferenceModule not attached | `drone.follow_reference = FollowReferenceModule(drone=drone)` |
| Second terminal has no ROS nodes visible | Workspace not sourced | Run all three `source` commands (see §2) |
| Gazebo window doesn't open | X11 not forwarded | Run `xhost +local:root` on host before starting container |
