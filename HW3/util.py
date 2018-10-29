import config
import dummy
import gbn
import ss
import threading


# Factory method to construct transport layer.
def get_transport_layer(sender_or_receiver,
                        transport_layer_protocol_name,
                        msg_handler):
  assert sender_or_receiver == 'sender' or sender_or_receiver == 'receiver' # extra control
  if sender_or_receiver == 'sender':
    return _get_transport_layer_by_name(config.ROLE_TYPE_SENDER,
                                        transport_layer_protocol_name,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        msg_handler)
  if sender_or_receiver == 'receiver':
    return _get_transport_layer_by_name(config.ROLE_TYPE_RECEIVER,
                                        transport_layer_protocol_name,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        msg_handler)

# private helper function og get_transport_layer()
def _get_transport_layer_by_name(role, name, local_ip, local_port, 
                                 remote_ip, remote_port, msg_handler):
  assert name == 'dummy' or name == 'ss' or name == 'gbn' # extra control
  if name == 'dummy':
    return dummy.DummyTransportLayer(role, local_ip, local_port,
                                     remote_ip, remote_port, msg_handler)
  if name == 'ss':
    return ss.StopAndWait(role, local_ip, local_port,
                          remote_ip, remote_port, msg_handler)
  if name == 'gbn':
    return gbn.GoBackN(role, local_ip, local_port,
                       remote_ip, remote_port, msg_handler)


# Convenient class to run a function periodically in a separate thread.
# A Timer
class PeriodicClosure:
  def __init__(self, handler, interval_sec):
    self._handler = handler
    self._interval_sec = interval_sec
    self._lock = threading.Lock()
    self._timer = None

  def _timeout_handler(self):
    with self._lock:
      self._handler()
      self.start()

  def start(self):
    self._timer = threading.Timer(self._interval_sec, self._timeout_handler)
    self._timer.start()

  def stop(self):
    with self._lock:
      if self._timer:
        self._timer.cancel()


# make packet for network layer to send
# CONTRACT: INT, INT, BYTES, INT -> BYTES
def make_pkt(msg_type, sequence_number, checksum, msg):
  sndpkt = None
  msg_type_bytes = int(msg_type).to_bytes(2,'big')
  seq_bytes = int(sequence_number).to_bytes(2,'big')
  checksum_bytes = int(checksum).to_bytes(2,'big')
  sndpkt = b''.join([msg_type_bytes, seq_bytes, checksum_bytes, msg])
  return sndpkt

# calculate the checksum of a msg
# CONTRACT: bytes -> 2-byte integer
def calculate_checksum(msg):
  msg_lenth = len(msg)
  if msg_lenth < 2:
    return 0
  if msg_lenth == 2:
    return int.from_bytes(msg[0:2],'big')
  checksum = int.from_bytes(msg[0:2],'big')
  i = 2
  while (i + 2) < msg_lenth:
    cur_two_bytes = msg[i:i+2]
    cur_int = int.from_bytes(cur_two_bytes,'big')
    checksum = (checksum + cur_int) % 10000
    i += 2
  return checksum

