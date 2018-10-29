# Usage: python demo_sender.py [dummy|ss|gbn]
import sys
import util
import time


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print('Usage: python demo_sender.py [dummy|ss|gbn]')
    sys.exit(1)

  transport_layer = None
  transport_layer_protocol_name = sys.argv[1]
  start_time = time.time()  
  try:
    transport_layer = util.get_transport_layer('sender',
                                               transport_layer_protocol_name,
                                               None)                                         
    for i in range(20):
      msg = 'MSG:' + str(i)
      print(msg)
      while not transport_layer.send(str.encode(msg)): # while transport layer fail send msg, pass
        continue
  finally:
    if transport_layer:
      transport_layer.shutdown()
    
