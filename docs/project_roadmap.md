# Orynth — Project Roadmap

> **Status note:** This file is kept as a milestone narrative. The authoritative
> architecture and deliverables now live in [System Architecture](system_architecture.md),
> [Deliverables Matrix](deliverables_matrix.md), and [ADR 0001](adr/0001-hybrid-control-stack.md).

---

## Vision

An autonomous multi-drone swarm system capable of coordinated perception, real-time mapping, and adaptive mission execution — deployable in simulation today, on commercial hardware tomorrow. The architecture separates concerns cleanly: the Mothership owns intelligence and aggregation, the Support Fleet owns edge sensing and redundancy.

---

## System Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│                        GROUND STATION                           │
│   Mission Planner · Fleet Monitor · Map Viewer · Data Store     │
│                    (Laptop / ThinkPad)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ Zenoh mesh
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐           ┌─────────────────────────────────┐
│   MOTHERSHIP    │           │         SUPPORT FLEET           │
│    (Drone 0)    │◄──────────│      (Drones 1 – 4)             │
│                 │           │                                 │
│ • Path planning │           │ • Onboard detection             │
│ • LiDAR fusion  │           │ • Local localization            │
│ • Map building  │           │ • Formation keeping             │
│ • RF routing    │           │ • Sensor redundancy             │
│ • Command relay │           │ • Visual servoing               │
└─────────────────┘           └─────────────────────────────────┘
```

---

## Phase 1 — Simulation Foundation

**Goal:** Full 5-drone simulation stack running end-to-end, all drones commandable.

### Work
- Per-drone Aerostack2 control stack (platform, state estimator, controller, behavior servers) launched for all 5 drones
- Coordinated takeoff and landing — all 5 drones arm, lift, and descend together
- Formation hold verified — flock orchestrator confirmed working against live odometry
- Zenoh router integrated as a startup process, warning eliminated
- Multi-terminal workflow documented and tested (`docker exec`)

### Deliverables
- `drone_stack_launch.py` — reusable per-drone launch that starts the full Aerostack2 stack, parameterised by namespace
- `swarm_bringup_launch.py` — master launch that starts the simulation world + all 5 drone stacks in one command
- `mission_test.py` — script that commands drone0 through a simple waypoint sequence and verifies formation drones follow
- Verified `ros2 topic list` showing all expected namespaced topics for all 5 drones
- Updated README with the full multi-terminal bringup procedure

---

## Phase 2 — Ground Control Station

**Goal:** The operator has full situational awareness of the swarm and can command it — or any individual drone — at any time from the ground station.

### Tool: Foxglove Studio
Foxglove Studio is the GCS foundation. It connects to the ROS 2 graph via WebSocket, runs as a desktop application on the ThinkPad, and provides 3D visualisation, camera panels, and custom control interfaces out of the box. https://foxglove.dev/

### Mothership ↔ Ground Station Link
The Mothership acts as the bandwidth gateway between the swarm and the ground station. It forwards telemetry and detection results continuously (tiny messages), streams compressed thumbnails of all camera feeds, and serves the full-resolution feed only for whichever drone the operator is actively monitoring. At standard companion computer WiFi range (200–400m LOS), this architecture keeps total uplink bandwidth manageable.

### Work
- Foxglove Studio installed on the ThinkPad ground station
- Foxglove WebSocket bridge node running as part of the ground station bringup
- **3D swarm visualisation** — all 5 drone poses rendered in real time from their odometry topics, showing positions, formation shape, and trajectories
- **Swarm command panel** — custom Foxglove panel that publishes formation mode changes, takeoff, land, and RTL (Return to Launch) commands to the flock orchestrator
- **Individual drone control panel** — per-drone interface that sends waypoint and altitude commands through the shared mission command layer, overriding swarm coordination temporarily
- **Camera feed panel** — live compressed video stream from any selected drone, switchable between all 5
- **YOLO overlay** — detection bounding boxes and class labels composited over the camera feed in real time using Foxglove's image annotation layer; perception node publishes raw image and `DetectionArray` separately, Foxglove composites them without baking annotations into the stream
- **Telemetry panel** — battery, state, altitude, and link quality for each drone displayed simultaneously
- Bandwidth manager node on the Mothership — prioritises telemetry and detections over video, throttles camera streams based on available link throughput

### Deliverables
- `gcs_bringup_launch.py` — launches Foxglove WebSocket bridge and all ground station nodes in one command
- `bandwidth_manager_node.py` — Mothership-side node that manages stream priorities and throttles camera feeds to available link budget
- Foxglove layout file (`.json`) — pre-configured panel arrangement with 3D view, 5 telemetry readouts, camera panel, and swarm command panel, importable on any machine
- Custom Foxglove swarm control panel (React) — publishes formation commands and RTL to the orchestrator
- Custom Foxglove individual drone panel (React) — publishes waypoint goals to a selected drone through the shared mission command interface
- Simulation demo: operator watches 5 drones fly in formation in the 3D panel, switches one drone to manual waypoint control and returns it to formation, watches YOLO detections appear as overlays on the camera feed

---

## Phase 3 — Swarm Behaviour & Shared Command Layer

**Goal:** The swarm behaves as a coherent unit across multiple formation modes and exposes a backend-neutral command surface for operator and autonomy layers.

### Work
- Formation library — geometric primitives (diamond, line, V, circle, search-spread) switchable at runtime
- Coordinated manoeuvres — formation transitions execute without inter-drone collision
- Collision avoidance — drones maintain minimum separation envelope using velocity obstacles or potential fields
- Swarm state machine — defined states (Idle → Takeoff → Form → Mission → Land → Disarm) with clean transitions
- Drone failure handling — if a support drone drops out, remaining drones rebalance the formation
- Shared command/status API completed so Foxglove panels, missions, and backend adapters target the same control surface

### Deliverables
- `formation_library.py` — reusable formation geometry module
- `swarm_state_machine.py` — mission state manager
- `swarm_api.py` / `vehicle_adapter.py` extended as the stable command surface
- `collision_monitor.py` — inter-drone separation watchdog
- Simulation demo: 5 drones take off, transition through 3 formation shapes, one drone exits and re-enters formation, then land
- Command replay log showing the same mission commands can be consumed without simulator-specific UI logic

---

## Phase 4 — ArduPilot SITL Bootstrap

**Goal:** Validate the real-flight backend early enough that the project does not drift into Aerostack2-only assumptions.

### Work
- Stand up a separate ArduPilot SITL bringup profile using official `ardupilot_sitl` and `ardupilot_gz`
- Validate AP_DDS and the shared vehicle adapter on a single vehicle first
- Confirm the same high-level mission commands work for arm, takeoff, waypoint flight, and land in both Aerostack2 sim and ArduPilot SITL
- Define namespacing and multi-vehicle assumptions for the later 2-drone and 5-drone SITL expansion
- Keep the Gazebo split explicit: Aerostack2 remains on Fortress, ArduPilot SITL remains on its supported Gazebo stack

### Deliverables
- `ardupilot_bringup_launch.py` — single-vehicle SITL bringup sharing the mission-layer interface
- `ardupilot_adapter.py` — AP_DDS-backed control path wired to the shared command surface
- Parity demo: one mission script drives both Aerostack2 sim and ArduPilot SITL through the same command API
- Bringup note documenting simulator/version differences and namespace assumptions for later scale-out

---

## Phase 5 — Perception Pipeline

**Goal:** Each support drone runs real-time object detection, and the operator can inspect detections at the same time the swarm remains controllable.

### Work
- Camera sensor added to each drone model in `swarm_config.json` (RGB + optional depth)
- Detector node per drone — subscribes to camera topic, runs inference, publishes `DetectionArray`
- GPU inference confirmed working inside the container via NVIDIA passthrough
- Perception fusion node on the ground station — aggregates `DetectionArray` from all 4 support drones, deduplicates detections across overlapping fields of view, builds a shared `TrackedObjectArray`
- Human detection validation campaign run against the 50–100 m target range with distance-binned precision, recall, and latency reporting
- Mothership consumes the fused object map for path planning decisions

### Deliverables
- `yolo_perception_node.py` — ROS 2 node wrapping the current detector backend and publishing `DetectionArray`
- `perception_fusion_node.py` — multi-drone detection aggregator with spatial deduplication
- `swarm_config.json` updated with camera payloads per drone
- Benchmark: inference latency per drone at target framerate (target: >15 FPS per drone on GPU)
- Validation report: human detection quality by distance band with operator overlay screenshots
- Simulation demo: 5 drones detect and track a moving object, fused detections visualised in RViz / Foxglove

---

## Phase 6 — Mission Autonomy, Sensor Fusion & Mapping

**Goal:** The swarm executes search or survey missions autonomously and produces a semantic map from LiDAR and vision data.

### Work
- Behaviour tree mission architecture — missions defined as BT XML files, not hardcoded Python
- Search pattern execution — systematic area coverage using boustrophedon (lawn-mower) or spiral patterns across the swarm
- Target acquisition — on detection, swarm transitions from search to surround or track behaviour
- Mission prioritisation — multiple concurrent objectives managed via BT priority nodes
- Dynamic task allocation — if a support drone's battery drops, its perception task migrates to a neighbour
- LiDAR sensor added to Mothership model in `swarm_config.json`
- `ApproximateTimeSynchronizer` pipeline — correlates Mothership LiDAR `PointCloud2` with support drone `DetectionArray` streams, stamping detections with 3D positions
- Point cloud aggregation — as the Mothership moves, successive scans are merged into a growing map using ICP or NDT registration
- Semantic mapping — detected objects are projected into the 3D point cloud, producing a labelled map
- Store-and-forward architecture — drones accumulate data locally, Mothership batches and forwards processed map tiles to the ground station when bandwidth allows

### Deliverables
- Mission BT XML library (`search_and_track.xml`, `area_survey.xml`, `target_surround.xml`)
- `mission_executor.py` — loads and runs BT missions at runtime
- `task_allocator.py` — dynamic workload distribution across the swarm
- `lidar_fusion_node.py` — time-synchronised LiDAR + detection fusion
- `map_builder_node.py` — incremental point cloud registration and map accumulation
- `semantic_map_node.py` — object-annotated 3D map publisher
- `store_forward_node.py` — bandwidth-aware data relay from Mothership to ground station
- Simulation demo: swarm surveys an area, detects a target, adapts mission behaviour, and ground station receives a complete labelled 3D map at mission end

---

## Phase 7 — Hardware Transition

**Goal:** The swarm transitions from simulation to real drones only after multi-vehicle ArduPilot SITL parity, preflight checks, and load-tested operator workflows are in place.

### Work
- Hardware selection finalised — ArduPilot-compatible autopilot + companion SBC per drone
- Docker image adapted for companion computer deployment
- Multi-vehicle ArduPilot SITL expanded from the Phase 4 bootstrap to the formation and mission cases required for field readiness
- Zenoh mesh configured for real RF environment — router on ThinkPad ground station, each drone a Zenoh peer
- Hardware-in-the-loop (HIL) testing — ArduPilot FCU connected to companion / laptop, DDS bridge validated before flight
- Pre-flight safety checklist automated — arming blocked until all drones report healthy state estimator, GPS lock, and battery above threshold
- ArduPilot parameters tuned per airframe

### Deliverables
- Multi-vehicle SITL parity demo — formation and mission cases driven through the shared mission-layer interface
- `ardupilot_bringup_launch.py` — ArduPilot SITL and hardware bringup sharing the same mission-layer interface
- `preflight_check.py` — automated health gate that must pass before any arm command is accepted
- Zenoh router config for mesh networking across 5 drones + ground station
- Companion computer deployment script
- First outdoor flight: 2-drone formation hold, 30 seconds, controlled landing

---

## Summary

| Phase | Focus | Key Output |
|---|---|---|
| 1 | Simulation foundation | All 5 drones commandable, one-command bringup |
| 2 | Ground control station | Live swarm view, manual control, YOLO camera overlay |
| 3 | Swarm behaviour & command layer | Formation library, state machine, shared command surface |
| 4 | ArduPilot SITL bootstrap | Early AP_DDS validation against the same mission API |
| 5 | Perception pipeline | Per-drone detection, multi-drone fusion, distance validation |
| 6 | Mission autonomy & mapping | BT missions, semantic map, search/survey autonomy |
| 7 | Hardware transition | Real flight, HIL testing, ArduPilot integration |
