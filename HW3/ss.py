import udt
import config
import util
from threading import Lock
import copy

# Stop-And-Wait reliable transport protocol.
class StopAndWait:

  # # Constructor
  # Instantiates a stop and wait protocol
  # CONTRACT: str, str, str, str, msg_handler(function) -> StopAndWait
  # GIVEN: "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, role, local_ip, local_port, 
               remote_ip, remote_port, msg_handler):
    self.role = role
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.timer = util.PeriodicClosure(self.timeout_handler,config.TIMEOUT_MSEC/1000)
    # fields for a tl sender
    self.seq_pkt_delivered = -1
    self.seq_pkt_to_send = 0
    self.msg_to_send = None
    self.pkt_to_send = None
    self.lock = Lock()
    self.sender_arv_lock = Lock()
    # fields for a tl receiver
    self.seq_pkt_received = -1
    self.seq_pkt_to_receive = 0
    self.recvlock = Lock()

  # called to deal with send timeout
  def timeout_handler(self):
    if self.seq_pkt_to_send == self.seq_pkt_delivered + 1:
      return
    print('[sender] timeout ', self.pkt_to_send)
    self.network_layer.send(self.pkt_to_send)

  # "send" is called by application. Return true on success, false otherwise
  # aka: if the pacakge to send is initialized by the transport layer, you should not use this function
  # impl protocol to send packet from application layer.
  # call self.network_layer.send() to send to network layer.
  # CONTRACT: bytes -> boolean
  def send(self, msg):
    assert self.role == config.ROLE_TYPE_SENDER
    if self.seq_pkt_delivered + 1 == self.seq_pkt_to_send:
      self.lock.acquire()
      print('[sender] acquire lock')
      checksum_pkt_to_send = util.calculate_checksum(msg)
      sndpkt = util.make_pkt(config.MSG_TYPE_DATA, self.seq_pkt_to_send, checksum_pkt_to_send, msg)
      self.msg_to_send = copy.deepcopy(msg)
      self.pkt_to_send = util.make_pkt(config.MSG_TYPE_DATA, self.seq_pkt_to_send, checksum_pkt_to_send, self.msg_to_send)
      print('[sender] sndpkt ',sndpkt)
      self.network_layer.send(sndpkt)
      self.timer.start()
      self.seq_pkt_to_send += 1
      print('[sender] seq_pkt_delivered ', self.seq_pkt_delivered, ' seq_pkt_to_send ', self.seq_pkt_to_send)
      self.lock.release()
      print('[sender] release lock')
      return True
    else:
      return False
    

  # handle message as a sender
  def _handle_arrival_msg_as_sender(self,msg):
    type_arv = int.from_bytes(msg[0:2],'big')
    seq_pkt_to_receive = int.from_bytes(msg[2:4],'big')
    checksum_arv = int.from_bytes(msg[4:6],'big')
    if type_arv == config.MSG_TYPE_ACK and seq_pkt_to_receive == self.seq_pkt_to_send and checksum_arv == 0:
      self.timer.stop()
      self.seq_pkt_delivered += 1
      print('[sender] good msg, move on')
    elif type_arv == config.MSG_TYPE_ACK and seq_pkt_to_receive < self.seq_pkt_to_send:
      self.timer.stop()
      self.network_layer.send(self.pkt_to_send)
      self.timer.start()
      print('[sender] last pkt not success, resend')
    else:
      self.timer.stop()
      self.network_layer.send(self.pkt_to_send)
      self.timer.start()
      print('[sender] corrupted pkt, resend')

  # handle message as a receiver
  def _handle_arrival_msg_as_receiver(self,msg):
    self.recvlock.acquire()

    type_pkt_arv = int.from_bytes(msg[0:2],'big')
    seq_pkt_arv = int.from_bytes(msg[2:4],'big')
    checksum_pkt_arv = int.from_bytes(msg[4:6],'big')
    audit_checksum = util.calculate_checksum(msg[6:])
    
    if type_pkt_arv == config.MSG_TYPE_DATA and seq_pkt_arv == self.seq_pkt_to_receive and checksum_pkt_arv == audit_checksum:
      self.msg_handler(msg)
      self.seq_pkt_received += 1
      self.seq_pkt_to_receive += 1
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      self.network_layer.send(ackpkt)
      print('[receiver] good msg, -> application')
    elif type_pkt_arv == config.MSG_TYPE_DATA and seq_pkt_arv < self.seq_pkt_to_receive:
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      self.network_layer.send(ackpkt)
      print('[receiver] dated msg, ignore')
    else:
      ackpkt = util.make_pkt(config.MSG_TYPE_ACK,self.seq_pkt_to_receive,0,b'')
      self.network_layer.send(ackpkt)
      print('[receiver] corrupted msg, ignore')

    self.recvlock.release()


  # "handler" to be called by network layer when packet is ready.
  # impl protocol to handle arrived packet from network layer.
  # call self.msg_handler() to deliver to application layer.
  # CONTRACT: -(deliver message to application layer)-> void
  def handle_arrival_msg(self):
    msg = self.network_layer.recv()
    if self.role == config.ROLE_TYPE_SENDER:
      self._handle_arrival_msg_as_sender(msg)
    elif self.role == config.ROLE_TYPE_RECEIVER:
      self._handle_arrival_msg_as_receiver(msg)
    

  # Cleanup resources.
  # cleanup anything else you may have when implementing this class.
  def shutdown(self):
    while self.seq_pkt_delivered + 1 != self.seq_pkt_to_send:
      continue
    self.network_layer.shutdown()
