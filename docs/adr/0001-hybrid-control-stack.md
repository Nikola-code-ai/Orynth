# ADR 0001: Hybrid Control Stack

- Status: Accepted
- Date: 2026-04-26

## Context

The repository already has a working `Aerostack2 + Gazebo Fortress` swarm
simulation. The target deployment, however, is an `ArduPilot`-based real
aircraft system with simulation-to-hardware continuity.

Older repo material blurred three different paths:

- Aerostack2 simulation behavior development
- PX4-oriented Aerostack2 hardware integration
- ArduPilot-based hardware and SITL integration

That ambiguity is expensive. It leads to wrong package choices, wrong
documentation references, and false assumptions about what can be swapped by
changing a single platform plugin.

## Decision

Adopt a hybrid control stack:

1. Keep Aerostack2 as the active swarm-development environment for simulation.
2. Treat ArduPilot as the authoritative real-flight and SITL path.
3. Route high-level swarm commands through a backend-neutral vehicle adapter.
4. Use `CycloneDDS` as the default repo middleware for development.
5. Evaluate `Zenoh` as a field-network option, not a blanket default.
6. Prefer ArduPilot `AP_DDS` for ROS 2 integration; use `MAVROS` as a fallback
   bridge where needed.

## Consequences

### Positive

- The current working simulation remains useful and does not need to be thrown
  away.
- The repo gets a cleaner separation between mission logic and vehicle backend.
- ArduPilot integration can be added without rewriting formation logic again.
- Documentation can point to official upstreams without pretending the current
  sim stack already matches the future flight stack.

### Costs

- The repo now has two simulation tracks to manage:
  Aerostack2/Gazebo Fortress
  ArduPilot/AP_DDS/ardupilot_gz
- ArduPilot SITL bringup will need its own launch and dependency profile.
- Some older docs remain historical and should not be treated as architecture
  authority.

## Follow-up Work

- Add the ArduPilot SITL adapter implementation.
- Add a dedicated ArduPilot bringup profile and documentation.
- Add Foxglove operator tooling on top of the shared mission layer.
- Add measurable bandwidth and detection benchmarks before field trials.
