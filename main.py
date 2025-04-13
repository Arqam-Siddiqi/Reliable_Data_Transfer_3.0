import time
import random

time_to_send = 0.5
timeout = 1.0
window_size = 3

random.seed(1)

class Segment:
    def __init__(self, index, data):
        self.index = index
        self.data = data
        self.checksum = calc_checksum(data)

def calc_checksum(data):
    return sum(1 for bit in data if bit == '1')

def simulate_unreliable_channel(segment: Segment):

    # Probability of packet loss
    if random.random() < 0.3:
        print(f"Channel: Packet {segment.data} lost in transit.")
        segment.data = None  
        segment.checksum = None
        return
    
    # Probability of packet corruption
    if random.random() < 0.2:
        segment.checksum += 1

    return segment

class RDTReceiver:
    def __init__(self, data_packet_count):
        self.data_packet_count = data_packet_count
        self.acked = [False] * data_packet_count
        
        self.expected_stop_and_wait = 0
        self.expected_gobackn = 0
        self.received_selective = [None] * data_packet_count
        self.expected_selective = 0

    def receive_stop_and_wait(self, segment: Segment):
        segment = simulate_unreliable_channel(segment)
        if segment is None:
            return False
        if segment.checksum != calc_checksum(segment.data):
            print(f"Receiver (Stop-and-Wait): Packet {segment.index} corrupted")
            return False
        if segment.index == self.expected_stop_and_wait:
            print(f"Receiver (Stop-and-Wait): Received expected packet {segment.index}: {segment.data}")
            self.acked[segment.index] = True
            self.expected_stop_and_wait += 1
            return True
        else:
            print(f"Receiver (Stop-and-Wait): Unexpected packet {segment.index}, expecting {self.expected_stop_and_wait}")
            return False

    def receive_gobackn(self, segment: Segment):
        segment = simulate_unreliable_channel(segment)
        if segment is None:
            return False
        if segment.checksum != calc_checksum(segment.data):
            print(f"Receiver (Go-Back-N): Packet {segment.index} corrupted")
            return False
        if segment.index == self.expected_gobackn:
            print(f"Receiver (Go-Back-N): Received expected packet {segment.index}: {segment.data}")
            self.acked[segment.index] = True
            self.expected_gobackn += 1
            return True
        else:
            print(f"Receiver (Go-Back-N): Out-of-order packet {segment.index}, expecting {self.expected_gobackn}")
            return False

    def receive_selective_repeat(self, segment: Segment):
        segment = simulate_unreliable_channel(segment)
        if segment is None:
            return False
        
        if segment.checksum != calc_checksum(segment.data):
            print(f"Receiver (Selective Repeat): Packet {segment.index} corrupted")
            return False
        
        if segment.index == self.expected_selective:
            print(f"Receiver (Selective Repeat): Received expected packet {segment.index}: {segment.data}")
            self.acked[segment.index] = True
            self.received_selective[segment.index] = segment.data
            self.expected_selective += 1

            while (self.expected_selective < self.data_packet_count and
                self.received_selective[self.expected_selective] is not None):
                print(f"Receiver (Selective Repeat): Delivering buffered packet {self.expected_selective}: {self.received_selective[self.expected_selective]}")
                self.acked[self.expected_selective] = True
                self.expected_selective += 1
            
            return True
        
        elif segment.index > self.expected_selective:

            if self.received_selective[segment.index] is None:
                self.received_selective[segment.index] = segment.data
                print(f"Receiver (Selective Repeat): Buffered out-of-order packet {segment.index}: {segment.data}")
            else:
                print(f"Receiver (Selective Repeat): Duplicate out-of-order packet {segment.index}")
            return True
        
        else:
            print(f"Receiver (Selective Repeat): Duplicate packet {segment.index}")
            return True

class RDTSender:
    def __init__(self, data_packet_count: int, data: list[str], receiver: RDTReceiver):
        self.data_packet_count = data_packet_count
        self.data = data

        global timeout, window_size

        self.timeout = timeout
        self.window_size = window_size
        self.receiver = receiver
        
    def stop_and_wait(self):
        for i in range(self.data_packet_count):
            ack_received = False
            while not ack_received:
                segment = Segment(i, self.data[i])

                print(f"Sender is currently sending packet {i}: {segment.data}")
                time.sleep(time_to_send) 
                ack_received = self.receiver.receive_stop_and_wait(segment)
               
                if ack_received:
                    print(f"Sender has received ACK for packet {i}\n")
                else:
                    print(f"Sender has not recieved ACK for packet {i}. Resending...\n")
                    time.sleep(self.timeout)

    def goback_n(self):
        base = 0
        while base < self.data_packet_count:
            window_end = min(base + self.window_size, self.data_packet_count)
            print(f"Sender Window: {list(range(base, window_end))}")

            for i in range(base, window_end):
                segment = Segment(i, self.data[i])
 
                print(f"Sender is currently sending packet {i}: {segment.data}")
                time.sleep(time_to_send)

            all_acked = True
            for i in range(base, window_end):
                segment = Segment(i, self.data[i])
                ack_received = self.receiver.receive_gobackn(segment)

                if ack_received:
                    print(f"Sender has received ACK for packet {i}\n")
                else:
                    print(f"Sender has not recieved ACK for packet {i}. Going back to packet {i}...\n")
                    base = i
                    time.sleep(self.timeout)
                    all_acked = False
                    break

            if all_acked:
                base = window_end
            print()

    def selective_repeat(self):
        acked = [False] * self.data_packet_count
        window = [i for i in range(self.window_size)]

        while not all(acked):
            print(f"Sender Window: {window}")

            for i in window:
                if not acked[i]:
                    segment = Segment(i, self.data[i])
                    
                    print(f"Sender is currently sending packet {i}: {segment.data}")
                    time.sleep(time_to_send)

            for i in window.copy():
                if not acked[i]:
                    segment = Segment(i, self.data[i])
                    
                    ack_received = self.receiver.receive_selective_repeat(segment)
                    if ack_received:
                        print(f"Sender has received ACK for packet {i}\n")
                        acked[i] = True
                        window.remove(i)
                    else:
                        print(f"Sender has not recieved ACK for packet {i}\n")

            for i in range(window_size - len(window)):
                for j in range(len(acked)):
                    if not acked[j] and j not in window and len(window) < window_size:
                        window.append(j)

            print()

packets_to_be_sent = ['0110011', '0110111', '01111101', '1111101', '11111111', '1111001']
num_of_packets_to_be_sent = len(packets_to_be_sent)

receiver = RDTReceiver(num_of_packets_to_be_sent)
sender = RDTSender(num_of_packets_to_be_sent, packets_to_be_sent, receiver)

print("\t\t\tStop-and-Wait Protocol:")
sender.stop_and_wait()

print("\n\n\n\t\t\tGo-Back-N Protocol:")
sender.goback_n()

print("\n\n\n\t\t\tSelective-Repeat Protocol:")
sender.selective_repeat()