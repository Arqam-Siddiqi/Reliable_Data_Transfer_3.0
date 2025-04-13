from network import Network, Packet, AckPacket
import time

class Rdt3Sender:
    def __init__(self, network, timeout=1.0, max_attempts=5):
        self.network: Network = network
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.current_seq_num = 0
        self.packet_sent = None
        self.timer_start = 0
    
    def send(self, data):
        # Create a packet with the current sequence number
        packet = Packet(self.current_seq_num, data)
        self.packet_sent = packet
        
        # Start the timer and send the packet
        self.timer_start = time.time()
        print(f"Sender: Sending packet {packet}")
        self.network.send_to_receiver(packet)
        
        # Wait for ACK or timeout
        attempts = 0
        while attempts < self.max_attempts:
            # Check if timeout has occurred
            if time.time() - self.timer_start > self.timeout:
                print(f"Sender: Timeout, resending packet {packet} (attempt {attempts+1}/{self.max_attempts})")
                self.timer_start = time.time()
                self.network.send_to_receiver(packet)
                attempts += 1
            
            # Check for ACK
            ack = self.network.receive_from_receiver()
            if ack:
                if not ack.is_corrupt() and ack.ack_num == self.current_seq_num:
                    print(f"Sender: Received ACK {ack}")
                    # Flip the sequence number for the next packet
                    self.current_seq_num = 1 - self.current_seq_num
                    return True
                else:
                    print(f"Sender: Received corrupt or wrong ACK {ack}")
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)
        
        print(f"Sender: Maximum attempts reached, giving up on packet {packet}")
        return False

class Rdt3Receiver:
    def __init__(self, network):
        self.network = network
        self.expected_seq_num = 0
    
    def receive(self):
        while True:
            packet = self.network.receive_from_sender()
            if packet:
                print(f"Receiver: Received packet {packet}")
                if not packet.is_corrupt() and packet.seq_num == self.expected_seq_num:
                    # Send ACK for the received packet
                    ack = AckPacket(packet.seq_num)
                    print(f"Receiver: Sending ACK {ack}")
                    self.network.send_to_sender(ack)
                    
                    # Flip the expected sequence number for the next packet
                    self.expected_seq_num = 1 - self.expected_seq_num
                    return packet.data
                else:
                    # Send ACK for the last correctly received packet
                    ack = AckPacket(1 - self.expected_seq_num)
                    print(f"Receiver: Sending ACK {ack} for previously received packet")
                    self.network.send_to_sender(ack)
            
            # Small delay to prevent CPU hogging
            time.sleep(0.01)