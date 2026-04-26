"""
Per-drone Gazebo bridge launcher with Gazebo TF disabled.

Aerostack2's upstream `drone_bridges.py` includes two Gazebo pose bridges:
  - /model/<name>/pose        -> /tf
  - /model/<name>/pose_static -> /tf

In this repository the state estimator is already the authoritative TF source
for flight control:
  earth -> <ns>/map -> <ns>/odom -> <ns>/base_link

Leaving Gazebo's pose bridges enabled creates competing parents for base_link
and intermittently splits the TF tree. We keep every other bridge but filter
out the `/tf` publishers so controllers and behaviors see a single TF graph.
"""

import json

from as2_gazebo_assets.utils.launch_exception import InvalidSimulationConfigFile
from as2_gazebo_assets.world import World

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction, Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def drone_bridges(context):
    """Return the filtered bridge nodes for a single drone namespace."""
    namespace = LaunchConfiguration('namespace').perform(context)
    config_file = LaunchConfiguration('simulation_config_file').perform(context)

    if config_file.endswith('.json'):
        with open(config_file, 'r', encoding='utf-8') as stream:
            config = json.load(stream)
    elif config_file.endswith(('.yaml', '.yml')):
        with open(config_file, 'r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
    else:
        raise InvalidSimulationConfigFile('Invalid configuration file extension.')

    world = World(**config)
    nodes = []

    for drone_model in world.drones:
        if drone_model.model_name != namespace:
            continue

        bridges, custom_bridges = drone_model.bridges(world.world_name)
        bridges = [bridge for bridge in bridges if bridge.ros_topic != '/tf']

        nodes.append(Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            namespace=drone_model.model_name,
            output='screen',
            arguments=[bridge.argument() for bridge in bridges],
            remappings=[bridge.remapping() for bridge in bridges],
        ))
        nodes += custom_bridges

    if not nodes:
        return [
            LogInfo(msg='Gazebo bridge creation failed.'),
            LogInfo(msg=f'Drone ID: {namespace} not found in {config_file}.'),
            Shutdown(reason='Aborting..'),
        ]

    return nodes


def generate_launch_description():
    """Generate launch description for per-drone Gazebo bridges."""
    return LaunchDescription([
        DeclareLaunchArgument(
            'simulation_config_file',
            description='JSON or YAML simulation configuration file',
        ),
        DeclareLaunchArgument(
            'namespace',
            description='Drone namespace to bridge',
        ),
        OpaqueFunction(function=drone_bridges),
    ])
