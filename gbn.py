import time
from network import Packet, AckPacket

class GbnSender:
    def __init__(self, network, window_size=4, timeout=1.0):
        self.network = network
        self.window_size = window_size
        self.timeout = timeout
        self.base = 0
        self.next_seq_num = 0
        self.packets = []  # Buffer for sent but unacked packets
        self.timer_start = 0
        self.timer_running = False
        self.max_attempts = 10  # Add maximum attempts to prevent infinite loops
        self.attempts = 0
    
    def send(self, data_list):
        all_sent = False
        all_acked = False
        
        while not all_acked and self.attempts < self.max_attempts:
            # Send new packets if window allows
            while not all_sent and self.next_seq_num < self.base + self.window_size:
                if self.next_seq_num < len(data_list):
                    packet = Packet(self.next_seq_num, data_list[self.next_seq_num])
                    print(f"GBN Sender: Sending packet {packet}")
                    self.network.send_to_receiver(packet)
                    if self.next_seq_num >= len(self.packets) + self.base:
                        self.packets.append(packet)
                    
                    # Start timer if this is the first packet in the window
                    if not self.timer_running:
                        self.timer_start = time.time()
                        self.timer_running = True
                    
                    self.next_seq_num += 1
                else:
                    all_sent = True
            
            # Check for timeout
            if self.timer_running and time.time() - self.timer_start > self.timeout:
                print(f"GBN Sender: Timeout, resending all packets from {self.base} to {self.next_seq_num-1}")
                for i in range(self.base, min(self.next_seq_num, len(data_list))):
                    packet_index = i - self.base
                    if packet_index < len(self.packets):
                        packet = self.packets[packet_index]
                        print(f"GBN Sender: Resending packet {packet}")
                        self.network.send_to_receiver(packet)
                self.timer_start = time.time()
                self.attempts += 1
            
            # Check for ACK
            ack = self.network.receive_from_receiver()
            if ack:
                if not ack.is_corrupt():
                    if ack.ack_num >= self.base:
                        print(f"GBN Sender: Received ACK {ack}")
                        # Update base and remove acknowledged packets from buffer
                        num_packets_acked = ack.ack_num - self.base + 1
                        
                        # Ensure we don't remove more packets than we have
                        num_packets_acked = min(num_packets_acked, len(self.packets))
                        
                        if num_packets_acked > 0:
                            self.packets = self.packets[num_packets_acked:]
                            self.base = ack.ack_num + 1
                        
                        # Reset attempts counter since we made progress
                        self.attempts = 0
                        
                        # Check if all packets are acknowledged
                        if self.base == len(data_list):
                            all_acked = True
                        
                        # Restart timer if there are still unacknowledged packets
                        if self.base < self.next_seq_num:
                            self.timer_start = time.time()
                        else:
                            self.timer_running = False
                    else:
                        print(f"GBN Sender: Received outdated ACK {ack}")
                else:
                    print(f"GBN Sender: Received corrupt ACK {ack}")
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        if self.attempts >= self.max_attempts:
            print("GBN Sender: Maximum attempts reached, giving up")
            return False
            
        return True

class GbnReceiver:
    def __init__(self, network):
        self.network = network
        self.expected_seq_num = 0
        self.received_data = []
    
    def receive(self, num_packets):
        timeout_start = time.time()
        timeout_duration = 10.0  # Add a timeout for the receiver too
        
        while len(self.received_data) < num_packets:
            # Check for timeout
            if time.time() - timeout_start > timeout_duration:
                print("GBN Receiver: Timeout, giving up")
                return self.received_data
                
            packet = self.network.receive_from_sender()
            if packet:
                print(f"GBN Receiver: Received packet {packet}")
                if not packet.is_corrupt() and packet.seq_num == self.expected_seq_num:
                    # Accept packet and send ACK
                    self.received_data.append(packet.data)
                    ack = AckPacket(packet.seq_num)
                    print(f"GBN Receiver: Sending ACK {ack}")
                    self.network.send_to_sender(ack)
                    self.expected_seq_num += 1
                    
                    # Reset timeout timer since we made progress
                    timeout_start = time.time()
                else:
                    # Send ACK for the last correctly received packet
                    last_ack = self.expected_seq_num - 1 if self.expected_seq_num > 0 else 0
                    ack = AckPacket(last_ack)
                    print(f"GBN Receiver: Sending ACK {ack} for last correctly received packet")
                    self.network.send_to_sender(ack)
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        return self.received_data