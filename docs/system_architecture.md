# Orynth System Architecture

This document is the authoritative architecture reference for the repository.
It supersedes older sections that implied a direct `PX4 -> Pixhawk` hardware
path. The target flight stack for real vehicles is `ArduPilot`.

## Current Reality

- The repository currently implements a working `Aerostack2 + Gazebo Fortress`
  simulation stack for a 5-drone swarm.
- The live control path in this repo is still simulation-first:
  `flock_orchestrator -> Aerostack2 behaviors -> as2_platform_gazebo -> Gazebo`
- Shared swarm logic now routes through a vehicle adapter boundary in code:
  `VehicleAdapter`
  `As2VehicleAdapter`
  `ArduPilotAdapter` placeholder

## Control Stack Split

| Track | Purpose | Status | Primary Upstream |
|---|---|---|---|
| `Aerostack2 simulation` | Formation logic, operator workflows, rapid swarm iteration | Implemented | Aerostack2 docs |
| `ArduPilot SITL` | Sim-to-real parity with the real FCU stack | Planned | ArduPilot AP_DDS + `ardupilot_sitl` + `ardupilot_gz` |
| `ArduPilot real flight` | Outdoor flight on real drones | Planned | ArduPilot AP_DDS, Micro XRCE-DDS Agent, MAVLink tooling |

## Design Decisions

### High-level swarm logic stays platform-neutral

- Formation state, mission state, operator commands, and safety policy must not
  call Aerostack2-only APIs directly.
- The shared control layer uses typed requests for:
  `takeoff`
  `land`
  `goto`
  `follow_reference`

### Aerostack2 remains the fast simulation path

- Aerostack2 already gives the repo working behavior servers, teleoperation,
  namespaced swarm launch, and follower formation control.
- This is the fastest place to develop:
  operator workflows
  formation switching
  failure handling
  perception plumbing

### ArduPilot is the real-flight truth path

- Real aircraft should be integrated through `AP_DDS` first.
- `MAVROS` remains a fallback bridge for capabilities that are mature there but
  not yet exposed cleanly through AP_DDS.
- The ArduPilot path should not be represented as a late plugin swap inside the
  existing Aerostack2 Gazebo launch. It is a separate bringup track with
  different upstream packages and different simulator expectations.

## Sensors and Compute Assumptions

- `5 x RGB cameras`
- `1 x LiDAR` on the leader drone
- `Jetson Orin Nano` class compute per drone
- Human detection target:
  `50-100 m`, daytime, stabilized camera, validated optics

## Communication Roles

| Role | Recommended Path |
|---|---|
| Swarm coordination | ROS 2 topics/actions |
| Simulation middleware | `rmw_cyclonedds_cpp` by default |
| Field middleware evaluation | `rmw_zenoh_cpp` in parallel benchmarks |
| ArduPilot FCU link | AP_DDS first |
| MAVLink/GCS interop | MAVProxy, QGroundControl, or MAVROS when needed |
| Operator video | Compressed unicast stream from selected drone |

## Sim-to-Real Path

1. Continue using the existing Aerostack2 simulation stack for swarm behavior.
2. Add an ArduPilot SITL profile using official `ardupilot_sitl` and
   `ardupilot_gz` packages.
3. Keep the mission layer identical across both tracks by targeting the shared
   adapter interface.
4. Graduate to real hardware only after SITL parity is demonstrated on the same
   mission interface.

## Important Constraint

The current repo uses `Gazebo Fortress` through Aerostack2. Current ArduPilot
ROS 2 Gazebo guidance recommends `Gazebo Harmonic` or `Garden` with the
`ardupilot_gz` stack. Treat that as a deliberate split, not a typo. The repo
should maintain separate simulation profiles rather than trying to force both
stacks through one Gazebo configuration.

## Official References

- ArduPilot ROS 2 overview: https://ardupilot.org/dev/docs/ros2.html
- ArduPilot ROS 2 SITL: https://ardupilot.org/dev/docs/ros2-sitl.html
- ArduPilot ROS 2 with Gazebo: https://ardupilot.org/dev/docs/ros2-gazebo.html
- ArduPilot ROS 2 interfaces: https://ardupilot.org/dev/docs/ros2-interfaces.html
- Aerostack2 architecture: https://aerostack2.github.io/_01_aerostack2_concepts/architecture/index.html
- Aerostack2 aerial platforms: https://aerostack2.github.io/_03_aerial_platforms/index.html
- Aerostack2 Pixhawk platform: https://aerostack2.github.io/_03_aerial_platforms/_pixhawk/index.html
