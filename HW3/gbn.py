import udt
import config
import util
from threading import Lock
from collections import deque
import copy
import time


# Go-Back-N reliable transport protocol.
class GoBackN:
  # "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, role, local_ip, local_port,
               remote_ip, remote_port, msg_handler):
    self.role = role
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.timer = util.PeriodicClosure(self.timeout_handler,config.TIMEOUT_MSEC/1000)
    self.starttime = time.time()
    # fields for a tl sender
    self.seq_pkt_delivered = -1
    self.seq_pkt_index = 0
    self.seq_pkt_window_left = 0
    self.seq_pkt_window_right = config.WINDOW_SIZE # not inclusive
    self.buffer = deque() # buffer of packages to send
    self.lock = Lock()
    # fields for a tl receiver
    self.seq_pkt_received = -1
    self.seq_pkt_to_receive = 0
    self.recvlock = Lock()

  def timeout_handler(self):
    self.lock.acquire()
    if self.seq_pkt_delivered + 1 >= self.seq_pkt_index:
      print('[sender] all pkts delivered. empty window')
      self.timer.stop()
      self.shutdown()
      self.lock.release()
      return
    for sndpkt in self.buffer:
      self.network_layer.send(sndpkt)
    self.lock.release()

  # "send" is called by application. Return true on success, false
  # otherwise.
  # impl protocol to send packet from application layer.
  # call self.network_layer.send() to send to network layer.
  def send(self, msg):
    assert self.role == config.ROLE_TYPE_SENDER
    if self.seq_pkt_index > self.seq_pkt_window_right:
      return False
    self.timer.stop()
    self.lock.acquire()
    sndpkt = util.make_pkt(config.MSG_TYPE_DATA,self.seq_pkt_index,util.calculate_checksum(msg),msg)
    self.network_layer.send(sndpkt)
    print('[sender] pkt ', self.seq_pkt_index,' sent')
    self.buffer.append(copy.deepcopy(sndpkt))
    self.seq_pkt_index += 1
    self.lock.release()
    self.timer.start()
    return True

  def _handle_arrival_msg_as_sender(self, msg):
    self.timer.stop()
    type_arv = int.from_bytes(msg[0:2],'big')
    seq_pkt_to_receive = int.from_bytes(msg[2:4],'big')
    checksum_arv = int.from_bytes(msg[4:6],'big')
    if type_arv == config.MSG_TYPE_ACK and seq_pkt_to_receive - 1 >= self.seq_pkt_window_left and seq_pkt_to_receive <= self.seq_pkt_window_right and checksum_arv == 0:
      self.lock.acquire()
      while self.seq_pkt_window_left < seq_pkt_to_receive:
        self.seq_pkt_delivered += 1
        self.seq_pkt_window_left += 1
        self.seq_pkt_window_right += 1
        if self.buffer:
          self.buffer.popleft()
      if seq_pkt_to_receive == self.seq_pkt_index:
        print('[sender] all pkt delivered up to now')
      self.lock.release()
    elif type_arv == config.MSG_TYPE_ACK and seq_pkt_to_receive <= self.seq_pkt_window_left:
      pass
    else:
      pass
    self.timer.start()

  def _handle_arrival_msg_as_receiver(self, msg):
    self.recvlock.acquire()
    type_pkt_arv = int.from_bytes(msg[0:2],'big')
    seq_pkt_arv = int.from_bytes(msg[2:4],'big')
    checksum_pkt_arv = int.from_bytes(msg[4:6],'big')
    audit_checksum = util.calculate_checksum(msg[6:])
    
    if type_pkt_arv == config.MSG_TYPE_DATA and seq_pkt_arv == self.seq_pkt_to_receive and checksum_pkt_arv == audit_checksum:
      print('[receiver] is perfect pkt ', seq_pkt_arv)
      self.msg_handler(msg[6:])
      self.seq_pkt_received += 1
      self.seq_pkt_to_receive += 1
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      print('[receiver] reply ackpkt',ackpkt)
      self.network_layer.send(ackpkt)
    elif type_pkt_arv == config.MSG_TYPE_DATA and seq_pkt_arv < self.seq_pkt_to_receive:
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      self.network_layer.send(ackpkt)
    else:
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      self.network_layer.send(ackpkt)

    self.recvlock.release()


  # "handler" to be called by network layer when packet is ready.
  # impl protocol to handle arrived packet from network layer.
  # call self.msg_handler() to deliver to application layer.
  def handle_arrival_msg(self):
    msg = self.network_layer.recv()
    if self.role == config.ROLE_TYPE_SENDER:
      self._handle_arrival_msg_as_sender(msg)
    elif self.role == config.ROLE_TYPE_RECEIVER:
      self._handle_arrival_msg_as_receiver(msg)

  # Cleanup resources.
  # cleanup anything else you may have when implementing this
  # class.
  def shutdown(self):
    while self.seq_pkt_delivered + 1 < self.seq_pkt_index:
      continue
    end_time = time.time()
    print('Time used [secs]:', end_time - self.starttime)
    print('[sender] finally shutdown')
    while self.timer:
      self.timer.stop()
    self.network_layer.shutdown()
