"""
Keyboard teleoperation launch file for AeroLab.

Launches the AS2 keyboard teleoperation GUI for one or more drones.
By default targets drone0 (the Mothership) with simulation time enabled.

Prerequisites:
  - swarm_bringup_launch.py must already be running
  - The drone(s) must be armed and in the air (use flock_orchestrator to take off,
    or manually: ros2 run as2_cli as2 takeoff -n drone0)

Usage (teleoperate drone0 only):
  ros2 launch aerolab_simulation teleop_launch.py

Usage (custom namespace):
  ros2 launch aerolab_simulation teleop_launch.py namespace:=drone0

Usage (multiple drones — comma-separated):
  ros2 launch aerolab_simulation teleop_launch.py namespace:=drone0,drone1

GUI Controls (from the keyboard teleoperation window):
  Arrow keys / WASD  — horizontal movement
  Q / E              — altitude up / down
  A / D              — yaw left / right
  Space              — hover (stop all motion)
  T                  — takeoff
  L                  — land

Note: PySimpleGUI is required (pre-installed in the aerolab_stack image).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument(
        'namespace',
        default_value='drone0',
        description='Drone namespace(s) to control. Comma-separated for multi-drone.'
    ))

    ld.add_action(IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('as2_keyboard_teleoperation'),
                'launch', 'as2_keyboard_teleoperation_launch.py'
            ])
        ]),
        launch_arguments={
            'namespace':     LaunchConfiguration('namespace'),
            'use_sim_time':  'true',
            'verbose':       'false',
        }.items()
    ))

    return ld
