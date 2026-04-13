# Swarm Networking Research

Research into communication protocols, middleware, and networking approaches for multi-drone swarm systems. Covers academic literature (2022–2025), open-source projects, and practical recommendations for the Orynth stack.

---

## Is Zenoh Standard?

**No — technically superior but not yet dominant.**

Zenoh achieved official ROS 2 endorsement in 2024 when OSRF selected it to complement existing DDS support. Binaries are available for ROS 2 Humble, Jazzy, and Rolling on Ubuntu (amd64, arm64). It holds Quality Level 2 classification — mature enough for production use, not yet at the Level 1 status of the most established implementations.

The broader ROS 2 community still defaults to **FastDDS** (eProsima) or **CycloneDDS** (Eclipse) because of legacy compatibility, tooling maturity, and community momentum. Zenoh is the best solution on paper that hasn't yet achieved mainstream adoption.

Benchmarks show Zenoh producing **97–99% less discovery traffic** than standard DDS configurations and outperforming FastDDS and CycloneDDS by an order of magnitude in dynamic mesh topologies — exactly the scenario a flying swarm presents.

**Sources:**
- Performance Comparison of ROS2 Middlewares for Multi-robot Mesh Networks in Planetary Exploration — https://link.springer.com/article/10.1007/s10846-024-02211-2
- Swarm Robot Communications in ROS 2: An Experimental Study (IEEE Access, 2024) — https://ieeexplore.ieee.org/document/10699316/
- ROS 2 Zenoh documentation — https://docs.ros.org/en/humble/Installation/RMW-Implementations/Non-DDS-Implementations/Working-with-Zenoh.html

---

## What Academic Research Uses (2022–2025)

Academic research converges on a **3-layer communication pattern**:

| Layer | Protocol | Purpose |
|---|---|---|
| Vehicle ↔ Flight controller | MAVLink / uXRCE-DDS | PX4 autopilot control |
| Inter-drone coordination | ROS 2 DDS (FastDDS or CycloneDDS) | Swarm topics and actions |
| Ground station relay | MQTT bridge or same DDS | Cloud or GCS connectivity |

Zenoh appears in papers and benchmarks but is rarely deployed in actual flying hardware implementations yet.

### Notable Papers and Projects

| System | Communication Stack | Source |
|---|---|---|
| Aerostack2 | ROS 2 + XRCE-DDS (PX4 bridge) + DDS | https://arxiv.org/html/2510.27327v1 |
| aerial-autonomy-stack | ROS 2 + XRCE-DDS, Docker-isolated virtual networks | https://arxiv.org/html/2602.07264v1 |
| ROS-based Multi-Domain Swarm | ROS 2 + MAVLink + MQTT bridge | https://www.mdpi.com/2226-4310/12/8/702 |
| DARPA SubT Challenge winners | LCM (Lightweight Communications and Marshalling) over custom UDP mesh | https://www.researchgate.net/publication/340269000 |
| ROS2swarm | ROS 2 DDS, single WiFi AP | https://arxiv.org/html/2405.02438v1 |

**Survey papers:**
- From Network Sensors to Intelligent Systems: A Decade-Long Review of Swarm Robotics Technologies (2025) — https://www.mdpi.com/1424-8220/25/19/6115
- Swarm Robotics: A Survey from a Multi-Tasking Perspective (ACM Computing Surveys, 2023) — https://dl.acm.org/doi/abs/10.1145/3611652

---

## Open-Source Project Choices

| Project | Middleware | Notes |
|---|---|---|
| CrazySwarm2 | ROS 2 CycloneDDS | Crazyflie proprietary radio + ROS 2 topics |
| Aerostack2 | ROS 2 + XRCE-DDS | PX4 uORB exposed as ROS 2 topics |
| aerial-autonomy-stack | ROS 2 + XRCE-DDS | Docker network isolation per drone |
| PX4 Multi-Vehicle | XRCE-DDS or MAVLink | Gazebo SITL simulation |
| flock2 (DJI Tello swarm) | ROS 2 DDS | Research project |

**Sources:**
- CrazySwarm2 — https://imrclab.github.io/crazyswarm2/
- Aerostack2 — https://aerostack2.github.io/
- aerial-autonomy-stack — https://github.com/JacopoPan/aerial-autonomy-stack
- PX4 multi-vehicle — https://docs.px4.io/main/en/ros2/multi_vehicle

---

## Protocol Comparison

### FastDDS (eProsima)
The most widely deployed ROS 2 middleware. Granular QoS control, better CPU efficiency in some scenarios. Higher discovery overhead and heavier memory footprint in mesh networks. Struggles on WiFi due to UDP multicast behaviour.

**Best for:** Industrial applications, wired networks, deterministic timing requirements.

### CycloneDDS (Eclipse)
Simpler than FastDDS, lower latency on Ethernet-based networks. Better CPU profile on constrained hardware. Also struggles with WiFi multicast flooding in mesh environments.

**Best for:** Embedded systems, local networks with guaranteed infrastructure, current best practice for outdoor WiFi swarms.

### Zenoh
Purpose-built for dynamic, lossy, heterogeneous networks. 97–99% reduction in discovery traffic vs DDS. Superior performance in topologies where nodes appear and disappear — exactly what a flying swarm produces. Smaller ecosystem and fewer community examples than DDS, but rapidly maturing.

**Best for:** Outdoor mesh networks, bandwidth-constrained environments, new projects starting from scratch. The forward-looking choice for 2025.

- https://zenoh.io/
- https://github.com/eclipse-zenoh/zenoh

### MAVLink
Lightweight point-to-point UDP protocol. The industry standard for UAV ↔ Ground Control Station communication. Not pub-sub and not designed for inter-robot swarm coordination. Supports 255 unique vehicle IDs. Used at the vehicle control layer alongside ROS 2, not as a replacement for it.

**Best for:** Vehicle ↔ GCS only. Not for drone-to-drone coordination.

### LCM (Lightweight Communications and Marshalling)
Originally designed for the 2006 MIT DARPA Urban Challenge. Pub-sub over UDP multicast with near-zero latency. Won the DARPA Subterranean Challenge. Less active development, smaller community, not ROS-integrated.

**Best for:** Extreme bandwidth constraints, proven in underground environments. Niche but battle-tested.

- https://github.com/lcm-proj/lcm

### MQTT Bridge
Decoupled pub-sub over TCP, cloud-friendly, standardised. Requires a bridge node to connect into ROS 2. Higher latency than native middleware due to extra hop. Useful for connecting ROS 2 swarms to cloud infrastructure or heterogeneous systems mixing ROS and non-ROS components.

**Best for:** Cloud connectivity, mixed ROS/non-ROS systems. Not for tight real-time coordination.

### eCAL (Eclipse Communication Abstraction Layer)
Emerging automotive-focused middleware with 1–20 GB/s throughput via automatic shared-memory selection. ROS 2 RMW adapter exists. Not widely deployed in robotics yet.

- https://github.com/eclipse-ecal/ecal
- https://github.com/eclipse-ecal/rmw_ecal

---

## WiFi Mesh Range

### Expected Ranges (Outdoor Line-of-Sight)

| Hardware | Band | Practical Reliable Range |
|---|---|---|
| Companion computer built-in WiFi (RPi5, Jetson) | 2.4 GHz | 150–300m |
| Companion computer built-in WiFi | 5 GHz | 80–200m |
| External high-gain omnidirectional USB adapter | 2.4 GHz | 500m–1km |
| **Doodle Labs Mesh Rider** | 900 MHz / 2.4 / 5 GHz | 1–5km |
| **Silvus StreamCaster** | Various | 5–30km |
| **Rajant Breadcrumb** | Various | 2–10km |
| LoRa fallback (emergency only) | Sub-GHz | 5–15km |

Drones at altitude help significantly — clean LOS to the ground station eliminates the multipath interference that degrades ground-level WiFi range.

### Mesh Topology

IEEE 802.11s (WiFi Mesh) with optimised routing is the recommended physical layer for outdoor swarms. Research shows customised routing metrics outperform the default Airtime metric for UAV applications.

Recommended routing protocols: HWMP (Hybrid Wireless Mesh Protocol), OLSR, or B.A.T.M.A.N. WiFi 6 (802.11ax) provides better QoS and throughput in congested bands.

Each mesh hop halves throughput and adds latency — relevant when drones spread out during search patterns. For the diamond formation at 3m spacing, drones are close enough that mesh hopping provides no range benefit; they all connect directly to the ground station.

**Sources:**
- IEEE 802.11s Mesh Routing for UAV Swarms — https://www.sciencedirect.com/science/article/abs/pii/S2542660520300998
- Low-Latency Wireless Mesh Networking for Drones & Robotics — https://www.unmannedsystemstechnology.com/2025/11/low-latency-wireless-mesh-networking-for-drones-robotics/

---

## Bandwidth Architecture

### Mothership as Gateway

The Mothership (Drone 0) acts as the bandwidth manager between the swarm and the ground station:

```
Support Drones (1–4)
    │
    │  Local WiFi mesh (short range, high bandwidth)
    │  • Raw detections (DetectionArray)
    │  • Compressed camera frames
    │
    ▼
Mothership (Drone 0)
    │
    │  Primary uplink to ground station
    │  • Always: telemetry, detection results (tiny)
    │  • Always: compressed thumbnails of all feeds
    │  • On demand: full-resolution camera feed (one drone at a time)
    │  • Batched: map tiles, point cloud segments
    │
    ▼
Ground Station (ThinkPad)
    • Foxglove Studio GCS
    • Zenoh router
    • Mission planner
```

### Uplink Budget Estimate (Standard WiFi at 200–300m)

| Data type | Bandwidth |
|---|---|
| Telemetry × 5 drones | ~0.1 Mbps |
| Detection results × 4 drones | ~0.5 Mbps |
| Compressed thumbnails × 4 drones (360p) | ~2 Mbps |
| Full camera feed × 1 drone (720p H.264) | ~3–5 Mbps |
| Map tile forwarding (batched) | ~1–2 Mbps |
| **Total** | **~7–10 Mbps** |

This fits within the practical throughput of 5 GHz WiFi at 200–300m LOS (~15–30 Mbps reliable). At longer ranges or degraded link conditions, the bandwidth manager drops camera quality before dropping telemetry or detections.

---

## LoRa Fallback Link

A separate low-power sub-GHz radio that carries only emergency commands — RTL (Return to Launch), land, and kill switch. Operates independently of the WiFi mesh. If the primary link drops at any range, the ground station retains the ability to recall the swarm.

Small, inexpensive, and the difference between a lost drone and a recovered one. Worth integrating from Phase 7 onwards.

---

## Recommendations for Orynth

| Scenario | Recommendation |
|---|---|
| Simulation (all phases) | Zenoh in peer-to-peer mode, no router needed |
| Early hardware testing (<100m) | Standard companion computer WiFi, Zenoh |
| Field operations (100–400m) | External high-gain USB WiFi adapter, Zenoh router on ThinkPad |
| Extended operations (>400m) | Doodle Labs Mesh Rider radios + LoRa fallback |

Zenoh is the right choice for this project: the swarm topology changes constantly as drones fly, Zenoh handles dynamic membership far better than DDS, and starting fresh means there is no legacy compatibility cost. The 97–99% discovery overhead reduction directly supports the bandwidth-segmented architecture already designed into the system.

**Comparison reference:** Comparison of DDS, MQTT, and Zenoh in Edge-to-Edge/Cloud Communication with ROS 2 — https://arxiv.org/abs/2309.07496
