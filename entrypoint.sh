#!/bin/bash
set -e

# Source ROS 2 base environment
source /opt/ros/humble/setup.bash

# Source Aerostack2 framework (official image compiles it at /root/aerostack2_ws)
if [ -f /root/aerostack2_ws/install/setup.bash ]; then
    source /root/aerostack2_ws/install/setup.bash
fi

# Source Aerostack2 CLI tools (as2 command, platform launchers)
export AEROSTACK2_PATH=/root/aerostack2_ws/src/aerostack2
if [ -f ${AEROSTACK2_PATH}/as2_cli/setup_env.bash ]; then
    source ${AEROSTACK2_PATH}/as2_cli/setup_env.bash
fi

# Source user overlay workspace if built
if [ -f /root/aerolab_ws/install/setup.bash ]; then
    source /root/aerolab_ws/install/setup.bash
fi

# Write all sources to ~/.bashrc so that `docker exec` terminals
# also get the full environment without manual sourcing.
if ! grep -q "aerostack2_ws" /root/.bashrc 2>/dev/null; then
    cat >> /root/.bashrc << 'EOF'

# AeroLab — auto-sourced by entrypoint.sh
source /opt/ros/humble/setup.bash
export AEROSTACK2_PATH=/root/aerostack2_ws/src/aerostack2
[ -f /root/aerostack2_ws/install/setup.bash ] && source /root/aerostack2_ws/install/setup.bash
[ -f ${AEROSTACK2_PATH}/as2_cli/setup_env.bash ] && source ${AEROSTACK2_PATH}/as2_cli/setup_env.bash
[ -f /root/aerolab_ws/install/setup.bash ] && source /root/aerolab_ws/install/setup.bash
EOF
fi

# RMW selection — set ORYNTH_RMW=zenoh to switch (default: cyclonedds)
if [ "$ORYNTH_RMW" = "zenoh" ]; then
    export RMW_IMPLEMENTATION=rmw_zenoh_cpp
    AEROLAB_SHARE=$(ros2 pkg prefix aerolab_simulation 2>/dev/null)/share/aerolab_simulation
    if [ -d "$AEROLAB_SHARE/config" ]; then
        export ZENOH_ROUTER_CONFIG_URI="$AEROLAB_SHARE/config/zenoh_router.json5"
        export ZENOH_SESSION_CONFIG_URI="$AEROLAB_SHARE/config/zenoh_session.json5"
    fi
fi

# Propagate RMW_IMPLEMENTATION to interactive shells (docker exec)
if ! grep -q "RMW_IMPLEMENTATION" /root/.bashrc 2>/dev/null; then
    echo "export RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION" >> /root/.bashrc
fi

exec "$@"
