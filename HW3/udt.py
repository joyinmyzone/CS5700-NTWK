import collections
import config
import random
import socket
import threading
import time
import util


class NetworkLayer:
  def __init__(self, local_ip, local_port, 
               remote_ip, remote_port, transport_layer):
    # Port for recv and send packets.
    self.remote_ip = remote_ip
    self.remote_port = remote_port
    # Listening on local_port to recv packets.
    self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.s.bind((local_ip, local_port))
    # self.s.setblocking(False)
    self.s.settimeout(0.5)  # seconds.
    # Hold transport layer object for message demultiplexing.
    self.transport_layer = transport_layer
    # Buffer for holding messages to be delivered to transport layer.
    self.msg_buffer = collections.deque(maxlen=8)
    self.buffer_lock = threading.Lock()
    # Start reading network packet thread.
    self.stop_accept_pkt = False
    # Periodically reading packets from socket.
    self.periodic_packet_receiver = util.PeriodicClosure(
      self._packet_reader, config.UDT_PACKET_RECV_INTERVAL_SEC)
    self.periodic_packet_receiver.start()
    # Periodically sending packets to transport layer.
    self.periodic_packet_deliver = util.PeriodicClosure(
      self._packet_deliver, config.UDT_PACKET_DELIVER_INTERVAL_SEC)
    self.periodic_packet_deliver.start()


  def shutdown(self):
    self.stop_accept_pkt = True
    self.periodic_packet_receiver.stop()
    self.periodic_packet_deliver.stop()


  # msg should be of type bytes, not string.
  def send(self, msg):
    if random.random() < config.BIT_ERROR_PROB:
      msg = self._random_bit_error(msg)
    if random.random() < config.MSG_LOST_PROB:
      return
    self.s.sendto(msg, (self.remote_ip, self.remote_port))


  def recv(self):
    msg = ''
    with self.buffer_lock:
      if len(self.msg_buffer) > 0:
        msg = self.msg_buffer.popleft()
    return msg


  def _packet_deliver(self):
    while not self.stop_accept_pkt:
      has_msg = False
      with self.buffer_lock:
        if len(self.msg_buffer) > 0:
          has_msg = True
      if has_msg:
        self.transport_layer.handle_arrival_msg()
        continue


  def _packet_reader(self):
    try:
      msg, addr = self.s.recvfrom(config.MAX_SEGMENT_SIZE)
      with self.buffer_lock:
        if len(self.msg_buffer) < self.msg_buffer.maxlen:
          self.msg_buffer.append(msg)
    except socket.timeout:
      # If timeout happens, just continue.
      pass


  # Return a new msg with random bit errors.
  def _random_bit_error(self, msg):
    l = len(msg)
    byte_index = random.randrange(l)
    prefix = msg[:byte_index]
    suffix = msg[byte_index+1:]
    original_byte = msg[byte_index]
    changed_byte = bytes([original_byte ^ 255])
    return prefix + changed_byte + suffix
