<div align="center">
  <h1>Orynth — AeroLab Swarm Architecture</h1>
  <p>Autonomous 5-Drone Swarm · ROS 2 Humble · Aerostack2 · Gazebo Sim · Docker</p>
</div>

---

## Overview

Orynth is a ground-up development environment for the coordination, simulation, and edge-compute AI deployment of a 5-drone multi-agent swarm. It is containerized from day one to ensure environment consistency across development machines and future deployment nodes.

The system is designed around a deliberate radio bandwidth architecture, segmenting network responsibilities so that the swarm can sustain heavy payload streams (LiDAR and 4K optics) without saturating the shared RF channel:

- **The Mothership (Drone 0)** — Central routing hub, global path planner, and LiDAR aggregator.
- **The Support Fleet (Drones 1–4)** — Decentralized edge workers dedicated to YOLOv11 computer vision and local localization.

> **Status:** Phase 1 complete. Full 5-drone simulation stack, teleoperation mode, and diamond formation flying are operational.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **OS** | Ubuntu 22.04 LTS |
| **Middleware** | ROS 2 Humble |
| **Swarm Framework** | Aerostack2 (official pre-built Docker base image) |
| **Simulation** | Ignition Gazebo Fortress (`as2_gazebo_assets`) |
| **Networking** | CycloneDDS (default) / Zenoh (alternative) |
| **Edge AI** | PyTorch + Ultralytics YOLOv11 |
| **Containerization** | Docker + Docker Compose |

---

## Architecture

The Docker setup follows the standard **ROS 2 underlay/overlay pattern**:

```
[ Docker Image (aerolab_stack) ]
  └── /opt/ros/humble/           ← ROS 2 Humble
  └── /root/aerostack2_ws/       ← Aerostack2 framework (pre-built in base image)

[ Host Volume Mount → /root/aerolab_ws/ ]  ← YOUR live code (live-edited on host)
  └── src/aerolab_simulation/
```

The image is built `FROM aerostack2/nightly-humble` — the official Aerostack2 Docker image which ships with ROS 2 Humble, Aerostack2 fully compiled, and Ignition Fortress pre-installed. Only project-specific additions (Zenoh RMW, Ultralytics, OpenCV headless) are added on top. Your source packages are mounted from the host at runtime for live editing — no rebuild required when you change Python logic.

### Per-Drone Stack

Each drone runs a full independent Aerostack2 stack under its namespace (`/drone0` through `/drone4`):

```
Gazebo physics
    ↕  (ros_gz_bridge: ground_truth, cmd_vel, arm, IMU)
as2_platform_gazebo        ← translates actuator commands → Gazebo, exposes sensors
as2_state_estimator        ← reads ground_truth bridge → publishes pose + TF
as2_motion_controller      ← PID: converts motion references → actuator commands
as2_behaviors_motion       ← action servers: Takeoff, GoTo, Land, FollowPath, FollowReference
```

The Gazebo↔ROS2 bridges are launched per-drone alongside the node stack.

---

## Implemented Features

### 1. Containerized Development Environment
A Dockerfile extending `aerostack2/nightly-humble` with PyTorch, Ultralytics YOLOv11, OpenCV (headless), and Eclipse Zenoh. The container exposes your GPU and X11 display for Gazebo rendering.

### 2. One-Command Swarm Bringup
`swarm_bringup_launch.py` starts the Gazebo world and all 5 drone stacks in a single command (plus the Zenoh router when `rmw:=zenoh`). Each stack includes the Gazebo bridges, platform node, state estimator, motion controller, and all 5 behavior action servers.

### 3. Teleoperation Mode
Fly drone0 interactively with a keyboard GUI (`teleop_launch.py`). Drones 1–4 automatically follow in diamond formation.

### 4. Automated Formation Mode
`flock_orchestrator` takes off all 5 drones simultaneously, then activates `FollowReferenceBehavior` on drones 1–4 relative to drone0's TF frame (`drone0/base_link`). The behavior updates in real time via TF as drone0 moves — no polling loop.

Diamond formation (offsets from drone0, FLU body frame — x forward, y left, z up):

```
         drone1 (+3m forward)
               ↑
drone2 (+3m left) ← drone0 → drone3 (3m right)
               ↓
         drone4 (3m rear)
```

---

## Quick Start

### Prerequisites (Host Machine)

- Docker + Docker Compose
- NVIDIA GPU with [`nvidia-container-toolkit`](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- X11 display server (standard on Ubuntu desktop)

### 1. Build the Docker Image

> Run this **once**, or any time you modify the `Dockerfile`. Takes 3–5 minutes.

```bash
docker compose build aerolab
```

### 2. Allow GUI Rendering (X11)

> Run this **once per host reboot**.

```bash
xhost +local:root
```

### 3. Start the Dev Container

> Run this **every coding session**.

```bash
cd aerolab_ws/
docker compose run --rm aerolab
```

You are now inside the container at `/root/aerolab_ws`.

### Switching RMW Middleware

CycloneDDS is the default and recommended RMW. To use Zenoh instead:

```bash
ORYNTH_RMW=zenoh docker compose run --rm aerolab
```

Then launch with:

```bash
ros2 launch aerolab_simulation swarm_bringup_launch.py rmw:=zenoh
```

Zenoh mode automatically starts the Zenoh router, configures IPv4 session endpoints, and launches the `tf_static_bridge` workaround node. No manual configuration needed.

### 4. Build Your Packages (inside container)

> Only needed when you add a package, change `package.xml`, `setup.py`, or `setup.cfg`. Normal Python edits are reflected immediately via the live volume mount.

```bash
colcon build
source install/setup.bash
```

### 5. Opening Additional Terminals

Every extra terminal needs the workspace sourced. `docker exec` bypasses the entrypoint, so source manually:

```bash
# On the host — open a second shell into the already-running container:
docker exec -it $(docker ps --filter ancestor=aerolab_stack --format '{{.Names}}' | head -1) bash

# Inside that shell:
source /opt/ros/humble/setup.bash
source /root/aerostack2_ws/install/setup.bash
source /root/aerolab_ws/install/setup.bash
```

---

## Running the Simulation

### Mode A — Teleoperation (fly drone0 manually, drones 1–4 follow)

**Terminal 1** — Start everything:
```bash
ros2 launch aerolab_simulation swarm_bringup_launch.py
```

Wait ~15 seconds for Gazebo to come up and all 5 drone stacks to finish launching. Verify in another shell:

```bash
ros2 node list | grep TakeoffBehavior | wc -l   # should print 5
```

**Terminal 2** — Take off all 5 drones and activate formation:
```bash
ros2 run aerolab_simulation flock_orchestrator
```

Wait for `Diamond formation ACTIVE. Drone0 is the leader.`

**Terminal 3** — Fly drone0 with keyboard:
```bash
ros2 launch aerolab_simulation teleop_launch.py
```

A GUI window opens. Drones 1–4 follow drone0 in real time.

---

### Mode B — Automated Formation (one-command bringup)

```bash
ros2 launch aerolab_simulation swarm_bringup_launch.py use_flock_orchestrator:=true
```

All 5 drones take off and enter diamond formation automatically. Then attach keyboard teleop in another terminal:

```bash
ros2 launch aerolab_simulation teleop_launch.py
```

---

### Phase 1 Validation Test

Run after the flock_orchestrator has established formation:

```bash
python3 /root/aerolab_ws/src/aerolab_simulation/scripts/mission_test.py
```

Commands drone0 through a waypoint sequence and verifies drones 1–4 hold their formation offsets at each stage. Prints `PASS`/`FAIL` per drone.

---

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Simulation foundation — 5 drones, teleop, formation | Complete |
| 2 | Ground control station — Foxglove GCS, live swarm view | Planned |
| 3 | Swarm behaviour — formation library, state machine, collision avoidance | Planned |
| 4 | Perception pipeline — YOLOv11 per drone, multi-drone fusion | Planned |
| 5 | Mission intelligence — BT missions, search/surround | Planned |
| 6 | Sensor fusion & mapping — LiDAR + vision, labelled 3D map | Planned |
| 7 | Hardware transition — Pixhawk 6C, companion computer, real flight | Planned |
