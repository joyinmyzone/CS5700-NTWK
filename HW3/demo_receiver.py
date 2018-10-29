# Usage: python demo_receiver.py [dummy|ss|gbn]
import config
import sys
import time
import util


def msg_handler(msg):
  print(repr(msg))


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print('Usage: python demo_receiver.py [dummy|ss|gbn]')
    sys.exit(1)

  transport_layer = None
  transport_layer_name = sys.argv[1]
  try:
    transport_layer = util.get_transport_layer('receiver',
                                               transport_layer_name,
                                               msg_handler) # instantiate a transport layer protocol
    while True:
      time.sleep(1)
  finally:
    if transport_layer:
      transport_layer.shutdown()
