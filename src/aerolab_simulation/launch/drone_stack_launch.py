"""
Per-drone Aerostack2 control stack launch file.

Starts the full Aerostack2 stack for a single drone under a given namespace:
  - drone_bridges          (Gazebo ↔ ROS2 topic bridges — cmd_vel, arm, ground_truth, IMU)
  - as2_platform_gazebo    (sim platform — connects Aerostack2 to Gazebo model)
  - as2_state_estimator    (ground truth state estimation)
  - as2_motion_controller  (PID speed controller)
  - takeoff_behavior_node   (TakeOff action server)
  - go_to_behavior_node     (GoTo action server)
  - land_behavior_node      (Land action server)
  - follow_path_behavior_node      (FollowPath action server)
  - follow_reference_behavior_node (FollowReference action server)

IMPORTANT: drone_bridges must be launched per-drone so that the ros_gz_bridge
nodes can forward Gazebo ground_truth, cmd_vel, and arm topics to ROS2.
Without these bridges the platform node has no data from Gazebo and cannot
send velocity commands back.

Usage (standalone, with Gazebo already running):
  ros2 launch aerolab_simulation drone_stack_launch.py namespace:=drone0

Usage (from swarm_bringup_launch.py):
  Included with launch_arguments={'namespace': 'droneN'}.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_drone_stack(context: LaunchContext, *args, **kwargs):
    """
    Build per-drone node list with namespace resolved at launch time.

    Using OpaqueFunction because the platform node parameters (cmd_vel_topic,
    arm_topic) must be constructed as plain strings including the namespace,
    and LaunchConfiguration substitutions cannot be embedded in f-strings at
    description-build time.
    """
    namespace = LaunchConfiguration('namespace').perform(context)

    # ── Config file paths ──────────────────────────────────────────────────────
    pkg_dir = get_package_share_directory('aerolab_simulation')
    platform_cfg   = os.path.join(pkg_dir, 'config', 'platform_gz.yaml')
    estimator_cfg  = os.path.join(pkg_dir, 'config', 'state_estimator.yaml')
    controller_cfg = os.path.join(pkg_dir, 'config', 'motion_controller.yaml')
    behaviors_cfg  = os.path.join(pkg_dir, 'config', 'behaviors.yaml')
    config_file    = os.path.join(pkg_dir, 'resource', 'swarm_config.json')

    as2_platform_gz_dir = get_package_share_directory('as2_platform_gazebo')
    control_modes_file = os.path.join(as2_platform_gz_dir, 'config', 'control_modes.yaml')

    actions = []

    # ── Drone bridges (Gazebo ↔ ROS2) — REQUIRED ──────────────────────────────
    # Creates three types of bridges for this drone:
    #   1. ground_truth_bridge: Gazebo model pose → /droneN/ground_truth/pose
    #      (state estimator reads this to publish self_localization + TF)
    #   2. cmd_vel bridge:  ROS2 /gz/droneN/cmd_vel → Gazebo /model/droneN/cmd_vel
    #      (platform node sends velocity commands through here)
    #   3. arm bridge:      ROS2 /gz/droneN/arm → Gazebo arm topic
    #   4. IMU bridge:      Gazebo IMU sensor → ROS2 sensor_measurements/imu
    #
    # We use the local bridge launcher instead of the upstream
    # as2_gazebo_assets launcher because Gazebo TF pose bridges conflict with
    # the AS2 state estimator's own earth->map->odom->base_link TF chain.
    drone_bridges = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_dir, 'launch', 'drone_bridges_launch.py')
        ),
        launch_arguments={
            'simulation_config_file': config_file,
            'namespace': namespace,
        }.items()
    )
    actions.append(drone_bridges)

    # ── Platform node ──────────────────────────────────────────────────────────
    # Bridges Aerostack2 to the Gazebo model for this drone.
    # cmd_vel_topic and arm_topic must match the bridge ros_topic values:
    #   cmd_vel bridge ros_topic: /gz/{model_name}/cmd_vel
    #   arm bridge ros_topic:     /gz/{model_name}/arm
    platform_node = Node(
        package='as2_platform_gazebo',
        executable='as2_platform_gazebo_node',
        name='platform',
        namespace=namespace,
        output='screen',
        parameters=[
            platform_cfg,
            {
                'use_sim_time': True,
                'control_modes_file': control_modes_file,
                'cmd_vel_topic': f'/gz/{namespace}/cmd_vel',
                'arm_topic':     f'/gz/{namespace}/arm',
                # acro_topic is only used in acro control mode (not used for quadrotor_base
                # with velocity control, but must be set to avoid publishing to topic "").
                'acro_topic':    f'/gz/{namespace}/acro',
            }
        ],
    )
    actions.append(platform_node)

    # ── State estimator node ───────────────────────────────────────────────────
    # Reads ground truth from ground_truth_bridge and publishes:
    #   /droneN/self_localization/pose  (PoseStamped)
    #   /droneN/self_localization/twist (TwistStamped)
    # Also broadcasts TF: earth → droneN/map → droneN/odom → droneN/base_link
    state_estimator_node = Node(
        package='as2_state_estimator',
        executable='as2_state_estimator_node',
        name='state_estimator',
        namespace=namespace,
        output='screen',
        parameters=[estimator_cfg, {'use_sim_time': True}],
    )
    actions.append(state_estimator_node)

    # ── Motion controller node ─────────────────────────────────────────────────
    controller_node = Node(
        package='as2_motion_controller',
        executable='as2_motion_controller_node',
        name='motion_controller',
        namespace=namespace,
        output='screen',
        parameters=[controller_cfg, {'use_sim_time': True}],
    )
    actions.append(controller_node)

    # ── Behavior nodes ─────────────────────────────────────────────────────────
    # as2_behaviors_motion ships 5 separate executables.
    # follow_reference_behavior_node has no plugin (it is self-contained).
    #
    # IMPORTANT: do NOT override the node name. The default C++ node name matches
    # the action name (e.g. "TakeoffBehavior"), and the behavior framework builds
    # its lifecycle services (_behavior/pause, _behavior/resume, _behavior/stop,
    # _behavior/modify) from `this->get_name() + "/_behavior/..."`. Renaming the
    # node (e.g. to "takeoff_behavior") places services at
    # /<ns>/takeoff_behavior/_behavior/pause while the action stays at
    # /<ns>/TakeoffBehavior, which as2_python_api's BehaviorHandler cannot find,
    # producing "BehaviorNotAvailable" warnings and preventing takeoff.
    behavior_executables = [
        ('takeoff_behavior_node',           'takeoff_plugin_position'),
        ('go_to_behavior_node',             'go_to_plugin_position'),
        ('land_behavior_node',              'land_plugin_speed'),
        ('follow_path_behavior_node',       'follow_path_plugin_position'),
        ('follow_reference_behavior_node',  ''),
    ]

    for executable, plugin in behavior_executables:
        params = [{'use_sim_time': True}, behaviors_cfg]
        if plugin:
            params.append({'plugin_name': plugin})
        actions.append(Node(
            package='as2_behaviors_motion',
            executable=executable,
            namespace=namespace,
            output='screen',
            parameters=params,
        ))

    return actions


def generate_launch_description():
    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument(
        'namespace',
        default_value='drone0',
        description='ROS 2 namespace for this drone (drone0, drone1, ...)'
    ))

    ld.add_action(OpaqueFunction(function=launch_drone_stack))

    return ld
