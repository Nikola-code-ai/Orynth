"""
Master swarm bringup launch file.

Starts the complete Orynth simulation stack with a single command:
  ros2 launch aerolab_simulation swarm_bringup_launch.py

Launch arguments:
  rmw  string  default='cyclonedds'  choices: cyclonedds, zenoh
      Select the ROS 2 middleware. When 'zenoh', the launch file starts a
      Zenoh router daemon, sets session config for IPv4 localhost, and runs
      the tf_static_bridge workaround node.

  use_flock_orchestrator  bool  default=false
      Start flock_orchestrator at bringup (takes off all 5 drones and activates
      diamond formation). Use this for automated formation mode.

Launch sequence — CycloneDDS (default):
  t=0s   Gazebo world + 5 drone model spawning
  t=6s   Per-drone Aerostack2 stacks x5 in parallel
  t=10s  Flock orchestrator (if use_flock_orchestrator:=true)

Launch sequence — Zenoh:
  t=0s   Zenoh router daemon (IPv4 on 0.0.0.0:7447)
  t=3s   Gazebo world + 5 drone model spawning
  t=11s  tf_static_bridge (Zenoh transient_local workaround)
  t=12s  Per-drone Aerostack2 stacks x5 in parallel
  t=16s  Flock orchestrator (if use_flock_orchestrator:=true)

Usage:
  ros2 launch aerolab_simulation swarm_bringup_launch.py
  ros2 launch aerolab_simulation swarm_bringup_launch.py rmw:=zenoh
  ros2 launch aerolab_simulation swarm_bringup_launch.py rmw:=zenoh use_flock_orchestrator:=true
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

DRONE_NAMESPACES = ['drone0', 'drone1', 'drone2', 'drone3', 'drone4']


def _build_launch_actions(context: LaunchContext, *args, **kwargs):
    """Build the full action list, branching on the 'rmw' launch argument."""
    rmw = LaunchConfiguration('rmw').perform(context)
    use_orch = LaunchConfiguration('use_flock_orchestrator').perform(context)
    is_zenoh = (rmw == 'zenoh')

    pkg_share = get_package_share_directory('aerolab_simulation')
    actions = []

    # ── RMW environment ───────────────────────────────────────────────────────
    if is_zenoh:
        actions.append(SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_zenoh_cpp'))
        actions.append(SetEnvironmentVariable(
            'ZENOH_ROUTER_CONFIG_URI',
            os.path.join(pkg_share, 'config', 'zenoh_router.json5'),
        ))
        actions.append(SetEnvironmentVariable(
            'ZENOH_SESSION_CONFIG_URI',
            os.path.join(pkg_share, 'config', 'zenoh_session.json5'),
        ))

    # ── Timer offsets ─────────────────────────────────────────────────────────
    if is_zenoh:
        gazebo_delay = 3.0
        stack_delay = 12.0
        bridge_delay = 11.0
        orch_delay = 16.0
    else:
        gazebo_delay = 0.0
        stack_delay = 6.0
        orch_delay = 10.0

    # ── Zenoh router (t=0s) ───────────────────────────────────────────────────
    if is_zenoh:
        actions.append(ExecuteProcess(
            cmd=['ros2', 'run', 'rmw_zenoh_cpp', 'rmw_zenohd'],
            name='zenoh_router',
            output='screen',
        ))

    # ── Gazebo world + drone model spawning ───────────────────────────────────
    gazebo_action = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'swarm_gazebo_launch.py')
        )
    )
    if gazebo_delay > 0:
        actions.append(TimerAction(period=gazebo_delay, actions=[gazebo_action]))
    else:
        actions.append(gazebo_action)

    # ── tf_static_bridge (Zenoh only) ─────────────────────────────────────────
    if is_zenoh:
        actions.append(TimerAction(
            period=bridge_delay,
            actions=[
                Node(
                    package='aerolab_simulation',
                    executable='tf_static_bridge',
                    name='tf_static_bridge',
                    output='screen',
                    parameters=[{'use_sim_time': True}],
                )
            ]
        ))

    # ── Per-drone Aerostack2 stacks (all 5 in parallel) ──────────────────────
    for ns in DRONE_NAMESPACES:
        actions.append(TimerAction(
            period=stack_delay,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg_share, 'launch', 'drone_stack_launch.py')
                    ),
                    launch_arguments={'namespace': ns}.items()
                )
            ]
        ))

    # ── Flock orchestrator (optional) ─────────────────────────────────────────
    if use_orch.lower() == 'true':
        actions.append(TimerAction(
            period=orch_delay,
            actions=[
                Node(
                    package='aerolab_simulation',
                    executable='flock_orchestrator',
                    name='flock_orchestrator',
                    output='screen',
                    parameters=[{'use_sim_time': True}],
                )
            ]
        ))

    return actions


def generate_launch_description():
    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument(
        'rmw',
        default_value=os.environ.get('ORYNTH_RMW', 'cyclonedds'),
        description="ROS 2 middleware: 'cyclonedds' (default) or 'zenoh'."
    ))

    ld.add_action(DeclareLaunchArgument(
        'use_flock_orchestrator',
        default_value='false',
        description=(
            'Start the flock_orchestrator at bringup. '
            'Takes off all 5 drones and activates diamond formation automatically.'
        )
    ))

    ld.add_action(OpaqueFunction(function=_build_launch_actions))

    return ld
