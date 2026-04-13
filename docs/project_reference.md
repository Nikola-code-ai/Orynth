# AeroLab Project Reference

Technical reference covering the AeroLab drone swarm stack — Docker setup, Aerostack2 architecture, PX4 integration, perception pipeline, and licensing.

---

## 1. Docker Setup

### Original Problem

Running `docker compose build aerolab` would freeze at build step 17/22 and crash with an out-of-memory error.

**Root cause:** Step 17 was `colcon build --symlink-install` — compiling the entire Aerostack2 framework from source inside the image. By default, `colcon build` spawns parallel compile jobs equal to the CPU core count. Each C++ compile job (especially in ROS 2) consumes 2–4 GB of RAM. With many cores, peak memory demand exceeded available RAM, causing the kernel to thrash swap then OOM-kill the build process.

### Additional Issues Found

| Issue | Problem |
|---|---|
| `ros-humble-ros-base` alongside `ros-humble-desktop` | Desktop is a superset of base — redundant |
| `ros-humble-ros-ign` + `ros-humble-ros-gz` | Same bridge under two names — potential conflict |
| `ignition-fortress` + `libignition-gazebo6-dev` | Fortress meta-package already includes the dev package |
| `ros-humble-behaviortree-cpp` + `ros-humble-behaviortree-cpp-v3` | Two incompatible major versions of BehaviorTree.CPP |
| `opencv-python` | Bundles GUI backends that conflict with ROS system OpenCV |

### Solution: Use the Official Aerostack2 Base Image

Aerostack2 publishes pre-built Docker images on Docker Hub:
- `aerostack2/nightly-humble:latest` — latest development build
- `aerostack2/humble:<version>` — stable release

The official image (`FROM osrf/ros:humble-desktop`) already includes:
- ROS 2 Humble desktop
- Aerostack2 fully compiled
- Ignition Fortress (via rosdep)
- `as2_ign_gazebo`, `as2_ign_gazebo_assets`
- `cv_bridge`, `sensor_msgs`, `geographic_msgs`
- `behaviortree_cpp` (v4)
- `colcon`, `rosdep`

### Final Dockerfile

```dockerfile
FROM aerostack2/nightly-humble:latest

# AI/ML dependencies
RUN pip3 install --no-cache-dir \
    ultralytics \
    opencv-python-headless \
    setuptools==58.2.0

# Both RMW implementations — switch at runtime via ORYNTH_RMW
RUN apt-get update && apt-get install -y \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-rmw-zenoh-cpp \
    && rm -rf /var/lib/apt/lists/*

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

ENV USER_WS=/root/aerolab_ws
RUN mkdir -p ${USER_WS}/src
WORKDIR ${USER_WS}

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
```

**Result:** Build time drops from 30+ minutes (with OOM crashes) to ~3–5 minutes.

### Entrypoint Sourcing Order

```bash
source /opt/ros/humble/setup.bash
source /root/aerostack2_ws/install/setup.bash                      # Aerostack2 framework
source /root/aerostack2_ws/src/aerostack2/as2_cli/setup_env.bash   # as2 CLI tools
source /root/aerolab_ws/install/setup.bash                         # user workspace (if built)
```

The official image puts Aerostack2 at `/root/aerostack2_ws` — the original entrypoint was pointing at the wrong path (`/opt/aerostack2_ws`).

### ros-gz vs ros-ign Conflict

Resolved by not installing either explicitly. The base image's rosdep handles the correct bridge packages for Ignition Fortress based on `as2_ign_gazebo`'s dependencies.

---

## 2. Aerostack2 Architecture

Aerostack2 is an autonomy middleware framework that runs on the companion computer. It abstracts the autopilot and provides a structured ROS 2 interface for building drone missions.

```
┌──────────────────────────────────────────┐
│           MISSION / BT LAYER             │  behavior trees, coordinator
├──────────────────────────────────────────┤
│           BEHAVIOR LAYER                 │  takeoff, go_to, follow, land
├──────────────────────────────────────────┤
│     PERCEPTION / CV / ML LAYER           │  detection, tracking, visual control
├──────────────────────────────────────────┤
│        MOTION CONTROL LAYER              │  controllers, reference handlers
├──────────────────────────────────────────┤
│          STATE ESTIMATION                │  pose, velocity, odometry fusion
├──────────────────────────────────────────┤
│           PLATFORM LAYER                 │  as2_platform_gazebo / pixhawk
└──────────────────────────────────────────┘
```

### Platform Layer

Abstracts the autopilot or simulator. Swapping platforms is the only change needed to move between simulation and hardware:

| Environment | Plugin |
|---|---|
| Simulation | `as2_ign_gazebo` |
| Real hardware | `as2_platform_pixhawk` |

### Behavior Layer

Each drone behavior is a ROS 2 action server:

| Action server | What it does |
|---|---|
| `TakeOffBehavior` | Arms, spins up, climbs to target height |
| `GoToPointBehavior` | Navigates to a 3D position |
| `FollowPathBehavior` | Follows a sequence of waypoints |
| `LandBehavior` | Controlled descent and disarm |
| `FollowReferenceBehavior` | Tracks a moving reference frame |

### Behavior Trees

`as2_behavior_trees` wraps action servers as BehaviorTree.CPP (v4) nodes. Complex missions are composed by connecting nodes — sequences, fallbacks, parallel execution — without hand-written state machines.

```
Mission BT
└── Sequence
    ├── TakeOff (all 5 drones, parallel)
    ├── FormDiamond (go_to_point per drone)
    ├── PatrolArea (follow_path)
    └── Land (all 5 drones, parallel)
```

### Swarm System

Each drone runs its own complete Aerostack2 stack under a ROS 2 namespace (`/drone0`, `/drone1`, etc.). A separate orchestrator node (`flock_orchestrator.py`) coordinates the swarm by sending goals to all drones simultaneously via their namespaced action servers:

```
flock_orchestrator
    ├── /drone0/go_to_point
    ├── /drone1/go_to_point
    ├── /drone2/go_to_point
    ├── /drone3/go_to_point
    └── /drone4/go_to_point
```

### Perception / Computer Vision System

`as2_perception` uses a plugin-based architecture. Any detector plugs into a standard interface:

```
Camera → sensor_msgs/Image
           ↓
    as2_perception node (detector plugin)
           ↓
    as2_msgs/DetectionArray  ←── standard output regardless of detector
           ↓
    Behavior / Controller
```

Visual servoing (`as2_vision_based_control`) closes the control loop on vision — the drone tracks a detected object by adjusting velocity based on its position in the camera frame.

### ML / AI Integration

Ultralytics and PyTorch are plain Python libraries. Integration is a single ROS 2 node:

```python
class YoloPerceptionNode(Node):
    def __init__(self):
        super().__init__('yolo_perception')
        self.model = YOLO('yolo11n.pt')        # pure ultralytics
        self.sub = self.create_subscription(
            Image, 'camera/image_raw', self.callback, 10)
        self.pub = self.create_publisher(
            DetectionArray, 'perception/detections', 10)

    def callback(self, msg):
        frame = bridge.imgmsg_to_cv2(msg)      # ROS image → numpy array
        results = self.model(frame)             # pure PyTorch inference
        self.pub.publish(self.to_as2(results))  # back into ROS 2
```

Everything inside `self.model(frame)` is vanilla PyTorch. The GPU passthrough already configured in `docker-compose.yml` means PyTorch automatically uses the GPU inside the container.

### Full Perception Data Flow

```
Gazebo publishes camera images per drone
    ↓
YOLO node per drone → DetectionArray per namespace
    ↓
flock_orchestrator aggregates all 5 detection streams
    ↓
Orchestrator decides swarm response (converge, surround, track)
    ↓
GoTo / FollowReference actions sent to each drone's behavior layer
    ↓
Behavior → motion controller → platform → Gazebo physics
```

---

## 3. PX4 vs Aerostack2

They are not alternatives — they operate at different layers and are used together on real hardware.

```
┌─────────────────────────────────────┐
│         YOUR MISSION CODE           │
├─────────────────────────────────────┤
│           AEROSTACK2                │  companion computer / ROS 2
├─────────────────────────────────────┤
│         PX4-AUTOPILOT               │  flight controller firmware
├─────────────────────────────────────┤
│         HARDWARE / PHYSICS          │  Pixhawk / Gazebo in sim
└─────────────────────────────────────┘
```

| Concern | PX4-Autopilot | Aerostack2 |
|---|---|---|
| Motor mixing & output | Yes | No |
| Attitude / rate control (PID) | Yes | No |
| Sensor fusion (IMU, GPS, baro) | Yes | No |
| State estimation (EKF) | Yes | No |
| Flight modes (takeoff, land, offboard) | Yes | Calls PX4 for these |
| Motion primitives (go_to, follow) | No | Yes |
| Behavior trees / mission logic | No | Yes |
| Multi-drone coordination | Minimal | Yes — first class |
| Platform abstraction | N/A | Yes |
| ROS 2 interface | Via uXRCE-DDS bridge | Native |

### PX4 Ecosystem

"PX4" refers to a broader ecosystem, not just the firmware:

- **PX4-Autopilot** — the flight controller firmware (`github.com/PX4/PX4-Autopilot`)
- **px4_msgs** — ROS 2 message definitions
- **uXRCE-DDS** — bridge connecting PX4-Autopilot to ROS 2
- **PX4-ROS2-Interface-Library** — helper library for offboard control
- **QGroundControl** — ground station software

### In Simulation

The current simulation stack has no PX4:

```
flock_orchestrator.py → Aerostack2 → as2_ign_gazebo → Ignition Gazebo physics
```

PX4 SITL can optionally be added for higher-fidelity simulation of flight controller behaviour at the cost of added complexity.

---

## 4. Moving to Hardware

The code stack stays identical. Only the platform plugin changes.

**Simulation:**
```
flock_orchestrator.py → Aerostack2 → as2_ign_gazebo → Ignition Gazebo
```

**Hardware:**
```
flock_orchestrator.py → Aerostack2 → as2_platform_pixhawk → uXRCE-DDS → PX4-Autopilot → Pixhawk
```

### Steps

1. **Flight controller**: Pixhawk 6C or 6X per drone, flashed with PX4-Autopilot firmware
2. **Companion computer**: Raspberry Pi 5, Jetson Orin Nano, or similar SBC per drone running ROS 2 + Aerostack2
3. **Launch file swap**: Replace `as2_ign_gazebo` launch with `as2_platform_pixhawk`, pointed at the Pixhawk serial port
4. **Networking**: Zenoh (already installed) handles unreliable multi-hop mesh networking between drones better than default FastDDS
5. **Ground station**: Laptop runs the orchestrator node, talking to all drones over WiFi/mesh radio via the same ROS 2 topics

### Intermediate Step: Hardware-in-the-Loop (HIL)

Connect a real Pixhawk to the laptop while Gazebo simulates physics and PX4 runs on real firmware. Good bridge between full simulation and flying hardware.

---

## 5. Industry Alternatives

| Framework | ROS 2 | Simulator | Swarm | Open Source |
|---|---|---|---|---|
| PX4 + ROS 2 | Full | Gazebo | Yes | Yes |
| ArduPilot + ROS 2 | Full | Gazebo | Yes | Yes |
| CrazySwarm2 | Full | CrazySim | Yes | Yes |
| AirSim (Microsoft) | Limited | Unreal Engine | Yes | Yes |
| Isaac Sim + Pegasus | Full | Isaac/Omniverse | Yes | Pegasus yes |
| FlytBase | Limited | — | Yes | No |
| Auterion Skynode | Limited | — | Yes | No |

- PX4 + ROS 2: https://docs.px4.io/main/en/ros2/multi_vehicle
- ArduPilot ROS 2: https://ardupilot.org/dev/docs/ros2.html
- CrazySwarm2: https://imrclab.github.io/crazyswarm2/
- AirSim: https://microsoft.github.io/AirSim/
- Pegasus Simulator: https://pegasussimulator.github.io/PegasusSimulator/
- FlytBase: https://www.flytbase.com/
- Auterion: https://auterion.com/

---

## 6. Licensing

### Aerostack2

**BSD-3-Clause** — consistent across all packages.

- Commercial use permitted
- No obligation to open source your own code
- Must retain copyright notice and disclaimer in distributed software/documentation
- Cannot use the Aerostack2 or UPM name to endorse products without written permission

### Full Stack Licensing

| Component | License | Commercial use |
|---|---|---|
| Aerostack2 | BSD-3-Clause | Yes, no source disclosure required |
| ROS 2 Humble | Apache 2.0 | Yes, no source disclosure required |
| PyTorch | BSD-style | Yes, no source disclosure required |
| Ignition Fortress | Apache 2.0 | Yes, no source disclosure required |
| Ubuntu 22.04 | Various (mostly GPL) | Yes, standard distro terms |
| **Ultralytics** | **AGPL-3.0** | **Requires commercial license** |

### Ultralytics Licensing Risk

AGPL-3.0 requires that if you distribute software using it — including software running on drones you sell — you must open source your entire application. Options:

1. **Ultralytics Enterprise License** — commercial license that removes the AGPL obligation
2. **Export model to ONNX and run via ONNX Runtime** (Apache 2.0) — removes the Ultralytics runtime from the distributed product entirely

### YOLO Version Selection

The `ultralytics` package contains all YOLO versions (v8, v9, v10, v11). Version is chosen at runtime by the weights file loaded:

```python
model = YOLO('yolo11n.pt')  # YOLOv11 — recommended
model = YOLO('yolov8n.pt')  # YOLOv8
```

**YOLOv11 is preferred**: faster inference at equivalent accuracy, smaller model size, better suited for edge deployment on companion computers. API is identical to v8.
