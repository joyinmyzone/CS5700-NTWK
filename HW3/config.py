# Port numbers used by unreliable network layers.
SENDER_IP_ADDRESS = '73.140.244.21'
SENDER_LISTEN_PORT = 8080
RECEIVER_IP_ADDRESS = '35.233.202.37'
RECEIVER_LISTEN_PORT = 8081

# Parameters for unreliable network.
BIT_ERROR_PROB = 0.5
MSG_LOST_PROB = 0.1

# Parameters for transport protocols.
TIMEOUT_MSEC = 150
WINDOW_SIZE = 20
SENDER_TIMEOUT = 1

# Packet size for network layer.
MAX_SEGMENT_SIZE = 512
# Packet size for transport layer.
MAX_MESSAGE_SIZE = 500
# Param for network layer.
UDT_PACKET_RECV_INTERVAL_SEC = 0.005
UDT_PACKET_DELIVER_INTERVAL_SEC = 0.005

# Message types used in transport layer.
MSG_TYPE_DATA = 1
MSG_TYPE_ACK = 2

# Role in transport layer
ROLE_TYPE_SENDER = 1
ROLE_TYPE_RECEIVER = 2

