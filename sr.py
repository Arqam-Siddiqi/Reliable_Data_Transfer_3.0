from network import Network, Packet, AckPacket
import time

class SrSender:
    def __init__(self, network, window_size=4, timeout=1.0):
        self.network = network
        self.window_size = window_size
        self.timeout = timeout
        self.base = 0
        self.next_seq_num = 0
        self.packets = {}  # Dictionary to store packets: {seq_num: (packet, timer_start)}
        self.acked = set()  # Set of acknowledged sequence numbers
    
    def send(self, data_list):
        all_sent = False
        all_acked = False
        
        while not all_acked:
            # Send new packets if window allows
            while not all_sent and self.next_seq_num < self.base + self.window_size:
                if self.next_seq_num < len(data_list):
                    packet = Packet(self.next_seq_num, data_list[self.next_seq_num])
                    print(f"SR Sender: Sending packet {packet}")
                    self.network.send_to_receiver(packet)
                    self.packets[self.next_seq_num] = (packet, time.time())
                    self.next_seq_num += 1
                else:
                    all_sent = True
            
            # Check for timeouts and resend packets
            current_time = time.time()
            for seq_num, (packet, timer_start) in list(self.packets.items()):
                if seq_num not in self.acked and current_time - timer_start > self.timeout:
                    print(f"SR Sender: Timeout for packet {packet}")
                    self.network.send_to_receiver(packet)
                    self.packets[seq_num] = (packet, current_time)
            
            # Check for ACKs
            ack = self.network.receive_from_receiver()
            if ack:
                if not ack.is_corrupt() and ack.ack_num >= self.base and ack.ack_num < self.next_seq_num:
                    print(f"SR Sender: Received ACK {ack}")
                    self.acked.add(ack.ack_num)
                    
                    # Update base (slide window) if possible
                    while self.base < self.next_seq_num and self.base in self.acked:
                        self.base += 1
                    
                    # Check if all packets are acknowledged
                    if self.base == len(data_list):
                        all_acked = True
                else:
                    print(f"SR Sender: Received corrupt or outdated ACK {ack}")
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        return True

class SrReceiver:
    def __init__(self, network, window_size=4):
        self.network = network
        self.window_size = window_size
        self.base = 0
        self.received_buffer = {}  # Buffer for out-of-order packets
        self.received_data = []
    
    def receive(self, num_packets):
        while len(self.received_data) < num_packets:
            packet = self.network.receive_from_sender()
            if packet:
                print(f"SR Receiver: Received packet {packet}")
                if not packet.is_corrupt():
                    # Check if packet is within the receiver's window
                    if self.base <= packet.seq_num < self.base + self.window_size:
                        # Accept packet, send ACK, and store it in buffer
                        self.received_buffer[packet.seq_num] = packet.data
                        ack = AckPacket(packet.seq_num)
                        print(f"SR Receiver: Sending ACK {ack}")
                        self.network.send_to_sender(ack)
                        
                        # Deliver in-order packets to application
                        while self.base in self.received_buffer:
                            self.received_data.append(self.received_buffer[self.base])
                            del self.received_buffer[self.base]
                            self.base += 1
                    # Packet is from old window, resend ACK
                    elif packet.seq_num < self.base:
                        ack = AckPacket(packet.seq_num)
                        print(f"SR Receiver: Resending ACK {ack} for old packet")
                        self.network.send_to_sender(ack)
                else:
                    print(f"SR Receiver: Received corrupt packet {packet}")
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        return self.received_data