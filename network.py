import random
import time
from queue import Queue, PriorityQueue
import threading

class Packet:
    def __init__(self, seq_num, data, checksum=None):
        self.seq_num = seq_num
        self.data = data
        self.checksum = checksum if checksum else self._calculate_checksum()
    
    def _calculate_checksum(self):
        # Simple checksum implementation
        return sum(bytearray(self.data, 'utf-8')) % 256
    
    def is_corrupt(self):
        return self.checksum != self._calculate_checksum()
    
    def __str__(self):
        return f"Packet(seq_num={self.seq_num}, data={self.data}, checksum={self.checksum})"


class AckPacket:
    def __init__(self, ack_num, checksum=None):
        self.ack_num = ack_num
        self.checksum = checksum if checksum else self._calculate_checksum()
    
    def _calculate_checksum(self):
        # Simple checksum implementation
        return self.ack_num % 256
    
    def is_corrupt(self):
        return self.checksum != self._calculate_checksum()
    
    def __str__(self):
        return f"AckPacket(ack_num={self.ack_num}, checksum={self.checksum})"


class Network:
    def __init__(self, loss_prob=0.1, corrupt_prob=0.1, delay_prob=0.1, max_delay=1.0):
        self.loss_prob = loss_prob
        self.corrupt_prob = corrupt_prob
        self.delay_prob = delay_prob
        self.max_delay = max_delay
        self.sender_to_receiver = Queue()
        self.receiver_to_sender = Queue()
        self.delayed_packets = PriorityQueue()
        self.running = True
        self.delay_thread = threading.Thread(target=self._process_delayed_packets)
        self.delay_thread.daemon = True
        self.delay_thread.start()
    
    def _process_delayed_packets(self):
        while self.running:
            if not self.delayed_packets.empty():
                delivery_time, (packet, destination) = self.delayed_packets.get()
                current_time = time.time()
                if delivery_time <= current_time:
                    if destination == "receiver":
                        self.sender_to_receiver.put(packet)
                    else:
                        self.receiver_to_sender.put(packet)
                else:
                    self.delayed_packets.put((delivery_time, (packet, destination)))
                    time.sleep(0.01)
            else:
                time.sleep(0.01)
    
    def send_to_receiver(self, packet):
        if random.random() < self.loss_prob:
            print(f"Packet lost: {packet}")
            return
        
        if random.random() < self.corrupt_prob:
            if hasattr(packet, 'data'):  # It's a data packet
                packet.data = packet.data + "_corrupted"
            else:  # It's an ACK packet
                packet.ack_num = (packet.ack_num + 1) % 256
            print(f"Packet corrupted: {packet}")
        
        if random.random() < self.delay_prob:
            delay = random.random() * self.max_delay
            delivery_time = time.time() + delay
            self.delayed_packets.put((delivery_time, (packet, "receiver")))
            print(f"Packet delayed by {delay:.2f}s: {packet}")
        else:
            self.sender_to_receiver.put(packet)
    
    def send_to_sender(self, packet):
        if random.random() < self.loss_prob:
            print(f"ACK lost: {packet}")
            return
        
        if random.random() < self.corrupt_prob:
            if hasattr(packet, 'data'):  # It's a data packet
                packet.data = packet.data + "_corrupted"
            else:  # It's an ACK packet
                packet.ack_num = (packet.ack_num + 1) % 256
            print(f"ACK corrupted: {packet}")
        
        if random.random() < self.delay_prob:
            delay = random.random() * self.max_delay
            delivery_time = time.time() + delay
            self.delayed_packets.put((delivery_time, (packet, "sender")))
            print(f"ACK delayed by {delay:.2f}s: {packet}")
        else:
            self.receiver_to_sender.put(packet)
    
    def receive_from_sender(self):
        if not self.sender_to_receiver.empty():
            return self.sender_to_receiver.get()
        return None
    
    def receive_from_receiver(self):
        if not self.receiver_to_sender.empty():
            return self.receiver_to_sender.get()
        return None
        
    def shutdown(self):
        self.running = False
        self.delay_thread.join(timeout=1.0)

