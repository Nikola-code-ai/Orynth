"""
Workaround for rmw_zenoh_cpp transient_local /tf_static replay bug.

Zenoh's publication cache does not correctly replay /tf_static messages from
multiple publishers to late-joining subscribers. This node subscribes to
/tf_static with TRANSIENT_LOCAL QoS, caches every transform by child_frame_id,
and republishes the full accumulated set at 1 Hz as VOLATILE messages.

Late-joining nodes (behavior servers, controllers) receive all static
transforms within 1 second of startup.

Only needed when RMW_IMPLEMENTATION=rmw_zenoh_cpp. The swarm_bringup_launch.py
conditionally starts this node when rmw:=zenoh.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy
from tf2_msgs.msg import TFMessage


class TfStaticBridge(Node):

    def __init__(self):
        super().__init__('tf_static_bridge')

        self._cache = {}  # child_frame_id -> TransformStamped

        static_qos = QoSProfile(
            depth=100,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_ALL,
        )
        volatile_qos = QoSProfile(
            depth=100,
            durability=DurabilityPolicy.VOLATILE,
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
        )

        self._sub = self.create_subscription(
            TFMessage, '/tf_static', self._on_tf_static, static_qos)
        self._pub = self.create_publisher(
            TFMessage, '/tf_static', volatile_qos)
        self._timer = self.create_timer(1.0, self._republish)

        self.get_logger().info(
            'tf_static_bridge: caching and republishing /tf_static at 1 Hz '
            '(Zenoh transient_local workaround)'
        )

    def _on_tf_static(self, msg):
        for t in msg.transforms:
            self._cache[t.child_frame_id] = t

    def _republish(self):
        if self._cache:
            msg = TFMessage(transforms=list(self._cache.values()))
            self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TfStaticBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
