# Orynth Deliverables Matrix

This file defines the milestone pipeline, expected evidence, and exit criteria
for the repository.

| Phase | Status | Deliverables | Exit Criteria | Evidence |
|---|---|---|---|---|
| 1A. Sim foundation | Complete | 5-drone Aerostack2 sim, formation hold, teleop, mission test | All 5 drones launch and maintain diamond formation | `swarm_bringup_launch.py`, `flock_orchestrator.py`, `mission_test.py` |
| 1B. Architecture hardening | Started | Hybrid architecture docs, shared formation geometry, vehicle adapter boundary | Repo docs no longer imply PX4 as the only hardware path; swarm logic is not hardwired to raw AS2 calls | `docs/system_architecture.md`, adapter modules, tests |
| 2. Operator workflow | Planned | Foxglove bridge bringup, saved layout, selected live stream, telemetry panel | Operator can monitor all drones and view one live feed without control degradation | launch file, Foxglove layout, recorded demo |
| 3. Swarm behavior & command API | Planned | Formation library, state model, per-drone override, abort/RTL logic, backend-neutral command/status surface | Manual leader and autonomous formation can be switched during a run through shared commands rather than backend-specific calls | mission replay, sim demo, command API doc |
| 4. ArduPilot SITL bootstrap | Planned | Separate ArduPilot SITL bringup, AP_DDS-backed adapter smoke path, single-vehicle arm/takeoff/goto/land flow | The same high-level command surface works in Aerostack2 sim and a single ArduPilot SITL vehicle | parity demo, launch docs, command log |
| 5. Perception | Planned | Onboard human detection on each RGB drone, tracked detections, distance validation, operator overlay | Detection latency and precision are reported by distance bucket and visualized in the operator workflow | benchmark report, rosbag replay, Foxglove capture |
| 6. Mission autonomy & mapping | Planned | Leader LiDAR map, semantic overlays, BT mission execution, survey/search behaviors | A search or survey mission can run end-to-end and produce a semantic map while one operator stream is active | map artifact, mission replay, BT mission files |
| 7. Real hardware | Planned | Multi-vehicle ArduPilot SITL parity, ArduPilot FCU integration, preflight checks, staged flight ladder | Single-drone, then 2-drone, then 5-drone trials pass acceptance gates after SITL parity and load testing | SITL logs, flight logs, checklists, incident notes |

## Acceptance Gates

- Every phase must define:
  a repeatable launch command
  a bounded demo scenario
  a rosbag or MCAP capture plan
  an abort criterion
- Backend-neutral command surfaces must be validated before new operator or autonomy workflows bind directly to a simulator-specific interface.
- No phase is complete if it only works interactively for the original author.
- Five-aircraft outdoor trials are blocked until:
  multi-vehicle ArduPilot SITL parity exists
  preflight checks are automated
  telemetry and operator video are measured under load
