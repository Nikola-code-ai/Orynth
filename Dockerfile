# Use the official Aerostack2 image as base.
# Includes: ROS 2 Humble desktop, Aerostack2 (compiled), Ignition Fortress (via rosdep),
# as2_ign_gazebo, cv_bridge, sensor_msgs, geographic_msgs, behaviortree_cpp, colcon, rosdep.
FROM aerostack2/nightly-humble:latest

# Install AI/ML dependencies
# opencv-python-headless avoids bundling GUI backends that conflict with ROS system OpenCV
RUN pip3 install --no-cache-dir \
    "numpy<2" \
    ultralytics \
    opencv-python-headless \
    setuptools==58.2.0

# Install both RMW implementations — switch at runtime via ORYNTH_RMW, no rebuild needed
RUN apt-get update && apt-get install -y \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-rmw-zenoh-cpp \
    && rm -rf /var/lib/apt/lists/*

# Default RMW — overridden by entrypoint.sh when ORYNTH_RMW=zenoh
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# User overlay workspace — populated at runtime via docker-compose volume mount
ENV USER_WS=/root/aerolab_ws
RUN mkdir -p ${USER_WS}/src
WORKDIR ${USER_WS}

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
