import os.path
import socket
import table
import threading
import util
import sys
import time

_CONFIG_UPDATE_INTERVAL_SEC = 5

_MAX_UPDATE_MSG_SIZE = 1024
_BASE_ID = 8000

def _ToPort(router_id):
  return _BASE_ID + router_id

def _ToRouterId(port):
  return port - _BASE_ID


class Router:
  # Instantiator
  def __init__(self, config_filename):
    # ForwardingTable has 3 columns (DestinationId,NextHop,Cost). It's
    # threadsafe.
    self._forwarding_table = table.ForwardingTable()
    self._distance_table = {} # Map<Destination,[NextHop,TotalCost]>
    self._distance_table_lock = threading.Lock()
    self._neighbors = [] # List<Integer>
    # Config file has router_id, neighbors, and link cost to reach
    # them.
    self._config_filename = config_filename
    self._router_id = None
    self._config_updater = None # a auto updater controller (PediodicClosure)
    # Socket used to send/recv update messages (using UDP).
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  
  def print_forwarding_table(self):
    print(f'----Router [{self._router_id}] Forwarding Table----')
    print('DEST\tNEXT\tCOST')
    for dst in self._forwarding_table._table.keys():
      pair = self._forwarding_table._table.get(dst)
      nxt = pair[0]
      cost = pair[1]
      print(dst,'\t',nxt,'\t',cost)
    print('------------------\n')

  def print_distance_table(self):
    print(f'----Router [{self._router_id}] Distance Table----')
    for dst in self._distance_table.keys():
      print(dst,':\t',self._distance_table.get(dst))
    print('------------------\n')


  # Start a router
  def start(self):
    # Start the Periodic Closure to update the distance table and forwarding table every 5 seconds
    self._config_updater = util.PeriodicClosure(
        self.load_config, _CONFIG_UPDATE_INTERVAL_SEC)
    self._config_updater.start()
    
    # PART I:
    # initialize the router's distance table and forwarding table
    with open(self._config_filename) as file:
      router_id = int(file.readline().strip())
      self._router_id = router_id
      self._socket.bind(('localhost', _ToPort(self._router_id)))
      self._distance_table[self._router_id] = {}
      for aline in file.readlines():
        record = aline.split(',')
        neighbor_id = int(record[0])
        cost = int(record[1])
        # Write into the distance table Map<Destination,Map<NextHop,TotalCost>>
        self._distance_table[neighbor_id] = {}
        self._distance_table.get(neighbor_id)[neighbor_id] = cost
        # Write into the forwarding table Map<Destination,[NextHop,TotalCost]>
        self._forwarding_table._table[neighbor_id] = [neighbor_id,cost] #[] is list in python
        # Initialize the neighbor list
        self._neighbors.append(neighbor_id)
    self.print_distance_table()
    self.print_forwarding_table()
    # prepare my first udpate message and broadcast it to my neighbors
    my_update_message = b''
    my_update_message += len(self._forwarding_table._table).to_bytes(2,'big')
    for dest in self._forwarding_table._table.keys():
      my_update_message += dest.to_bytes(2, 'big')
      my_update_message += self._forwarding_table._table[dest][1].to_bytes(2, 'big')
    for neighbor in self._neighbors:
      self._socket.sendto(my_update_message,('localhost',_ToPort(neighbor)))
    
    # PART II:
    # keep receiving update messages from my neighbors 
    # update my distance table and forwarding table
    while True:
      # If no message is received, continue receiving
      try:
        data, address = self._socket.recvfrom(_MAX_UPDATE_MSG_SIZE)
      except ConnectionResetError:
        continue
      print('Received Message From Router ', _ToRouterId(address[1]))
      # Update my distance table and forwarding table with the update message received
      entry_count = int.from_bytes(data[0:2], 'big')
      body = data[2:]
      src_r_id = _ToRouterId(address[1]) # The RouterID of the sender (IP, PORT)
      # STEP 1: Prepare the Map<Destination,Cost> pairs from neighbor n for updating two tables
      update_map = {} # Map<Destination,Cost>
      for i in range(entry_count):
        dest = int.from_bytes(body[i*4 : i*4+2], 'big')
        cost = int.from_bytes(body[i*4+2 : i*4+4], 'big')
        update_map[dest] = cost
      print('Update Message From Router[', src_r_id,']:',update_map)
      # STEP 2: update my distance table and forwarding table
      #    P.1  update the distance table
      self._forwarding_table._lock.acquire()
      self._distance_table_lock.acquire()
      link_cost = self._distance_table.get(src_r_id).get(src_r_id)
      for dst in update_map.keys():
        if dst == self._router_id:
          continue
        new_cost = update_map[dst] + link_cost
        if dst not in self._distance_table.keys():
          self._distance_table[dst] = {}
          self._distance_table[dst][src_r_id] = new_cost
        else:
          self._distance_table[dst][src_r_id] = new_cost
      #    P.2  update the forwarding table
      for dst in self._distance_table.keys():
        if dst == self._router_id:
          continue
        # Get the new best <Next, Cost> pair to Router[dst]
        best_next = None
        min_cost = sys.maxsize
        routes_to_dst = self._distance_table.get(dst)
        for nxt in routes_to_dst.keys():
          cur_cost = routes_to_dst.get(nxt)
          if cur_cost < min_cost:
            best_next = nxt
            min_cost = cur_cost
        # Update the forwarding table if necessary
        self._forwarding_table._table[dst] = [best_next, min_cost]
      self.print_forwarding_table()
      self._distance_table_lock.release()
      self._forwarding_table._lock.release()
    
      
  # stop a router
  def stop(self):
    if self._config_updater:
      self._config_updater.stop()
    # [official] clean up other threads.
    self._socket.close()


  # For a certain period, do the following things:
  # 1] retrive the up-to-date (neighbor,cost) pairs from the config
  # 2] update the distance table
  # 3] update the forwarding table
  # 4] broadcast a update message to all my neighbors
  def load_config(self):
    # STEP 1: Input the config info to a Map<Neigbhor,LinkCost>
    neighbor_link_cost_pairs = {} # Map<Neigbhor,LinkCost>
    assert os.path.isfile(self._config_filename)
    with open(self._config_filename) as file:
      router_id = int(file.readline().strip())
      # Only set router_id when first initialize.
      if not self._router_id:
        self._socket.bind(('localhost', _ToPort(router_id)))
        self._router_id = router_id
      # read Pair<Neighbor,LinkCost> pairs into Map<Neigbhor,LinkCost>
      for aline in file.readlines():
        aline = aline.strip()
        a_record = aline.split(',')
        a_neighbor = int(a_record[0])
        a_cost = int(a_record[1])
        neighbor_link_cost_pairs[a_neighbor] = a_cost

    # STEP 2: Update my distance table
    self._distance_table_lock.acquire()
    self._forwarding_table._lock.acquire()
    old_link_costs = {}
    for neighbor in self._neighbors:
      old_link_costs[neighbor] = self._distance_table.get(neighbor).get(neighbor)
    self.print_distance_table()
    for dst in self._distance_table.keys():
      if dst == self._router_id:
        continue
      routes_to_dst = self._distance_table.get(dst)
      for nxt in neighbor_link_cost_pairs.keys():
        old_link_cost = old_link_costs.get(nxt)
        new_link_cost = neighbor_link_cost_pairs.get(nxt)
        dif = new_link_cost - old_link_cost
        if routes_to_dst.get(nxt) == None:
          continue
        new_total_cost = routes_to_dst.get(nxt) + dif
        self._distance_table[dst][nxt] = new_total_cost
    self.print_distance_table()

    # STEP 3: Update my forwarding table and prepare the update message
    my_update_entries = b''
    my_entry_count = 0
    for dst in self._distance_table.keys():
      if dst == self._router_id:
        continue
      routes_to_dst = self._distance_table.get(dst)
      best_next = None
      min_cost = sys.maxsize
      for nxt in routes_to_dst.keys():
        cur_cost = routes_to_dst.get(nxt)
        if cur_cost < min_cost:
          best_next = nxt
          min_cost = cur_cost
      self._forwarding_table._table[dst] = [best_next, min_cost]
      my_entry_count += 1
      my_update_entries += dst.to_bytes(2,'big')
      my_update_entries += min_cost.to_bytes(2, 'big')

    # STEP 4: prepare my udpate message to my neighbors
    my_entry_count_bytes = int(my_entry_count).to_bytes(2,'big')
    my_update_message = b''.join([my_entry_count_bytes, my_update_entries])
    #         send update message to neighbors
    for neighbor in self._neighbors:
      self._socket.sendto(my_update_message,('localhost',_ToPort(neighbor)))
    self.print_forwarding_table()

    self._distance_table_lock.release()
    self._forwarding_table._lock.release()
