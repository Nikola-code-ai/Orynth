"""
Launch file for AeroLab 5-drone swarm in Gazebo Simulation using Aerostack2.
This launches the physics environment and spawns drone0 (Mothership) and drone1-4 (Support)
using a unified simulation_config.json block.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    ld = LaunchDescription()

    # Get the path to our local package and the resource config file
    pkg_dir = get_package_share_directory('aerolab_simulation')
    config_file = os.path.join(pkg_dir, 'resource', 'swarm_config.json')

    # The new unified Aerostack2 Gazebo Launcher
    # This automatically spawns the world and all drones listed in the JSON
    simulation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('as2_gazebo_assets'), 'launch', 'launch_simulation.py'
            ])
        ]),
        launch_arguments={
            'simulation_config_file': config_file
        }.items()
    )

    ld.add_action(simulation_launch)

    return ld
