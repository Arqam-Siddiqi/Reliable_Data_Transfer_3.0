import time
import random

time_to_send = 0.5
timeout = 1.0
window_size = 3

def calc_checksum(data):
    return sum(1 for bit in data if bit == '1')

class Segment:
    def __init__(self, index, data):
        self.index = index
        self.data = data
        self.checksum = calc_checksum(data)

def simulate_unreliable_channel(segment: Segment):
    if random.random() < 0.3:
        print(f"Channel: Packet {segment.data} lost in transit.")
        segment.data = None  
        segment.checksum = None
        return None
    
    if random.random() < 0.2:
        segment.checksum += 1

    return segment

class Receiver:
    def __init__(self, data_packet_count):
        self.data_packet_count = data_packet_count
        self.acked = [False] * data_packet_count
        
        self.expected_stop_and_wait = 0
        self.expected_gobackn = 0
        self.received_selective = [None] * data_packet_count

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
        if not self.acked[segment.index]:
            print(f"Receiver (Selective Repeat): Received packet {segment.index}: {segment.data}")
            self.acked[segment.index] = True
            self.received_selective[segment.index] = segment.data
            return True
        else:
            print(f"Receiver (Selective Repeat): Duplicate packet {segment.index}")
            return True

# Sender
class Sender:
    def __init__(self, data_packet_count: int, data: list[str], receiver: Receiver):
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

                print(f"Sender: Sending packet {i}: {segment.data}")
                time.sleep(time_to_send) 
                ack_received = self.receiver.receive_stop_and_wait(segment)
               
                if ack_received:
                    print(f"Sender: ACK received for packet {i}\n")
                else:
                    print(f"Sender: No ACK for packet {i}, timeout... Resending...\n")
                    time.sleep(self.timeout)

    def goback_n(self):
        base = 0
        while base < self.data_packet_count:
            window_end = min(base + self.window_size, self.data_packet_count)
            print(f"Sender: Sending window: {list(range(base, window_end))}")

            for i in range(base, window_end):
                segment = Segment(i, self.data[i])
 
                print(f"Sender: Sending packet {i}: {segment.data}")
                time.sleep(time_to_send)

            all_acked = True
            for i in range(base, window_end):
                segment = Segment(i, self.data[i])
                ack_received = self.receiver.receive_gobackn(segment)

                if ack_received:
                    print(f"Sender: ACK received for packet {i}")
                else:
                    print(f"Sender: No ACK for packet {i}, timeout... Go back to packet {i}\n")
                    base = i
                    time.sleep(self.timeout)
                    all_acked = False
                    break

            if all_acked:
                base = window_end
            print()

    def selective_repeat(self):
        base = 0
        acked = [False] * self.data_packet_count

        while base < self.data_packet_count:
            window_end = min(base + self.window_size, self.data_packet_count)
            print(f"Sender: Sending window: {list(range(base, window_end))}")

            for i in range(base, window_end):
                if not acked[i]:
                    segment = Segment(i, self.data[i])
                    
                    print(f"Sender: Sending packet {i}: {segment.data}")
                    time.sleep(time_to_send)

            for i in range(base, window_end):
                if not acked[i]:
                    segment = Segment(i, self.data[i])
                    
                    ack_received = self.receiver.receive_selective_repeat(segment)
                    if ack_received:
                        print(f"Sender: ACK received for packet {i}")
                        acked[i] = True
                    else:
                        print(f"Sender: No ACK for packet {i}, will retry later")

            while base < self.data_packet_count and acked[base]:
                base += 1

            print()

data_packets = ['1111001', '1110111', '110111', '11111101', '1111101', '11111111']

receiver = Receiver(data_packet_count=len(data_packets))
sender = Sender(data_packet_count=len(data_packets), data=data_packets, receiver=receiver)

# sender.stop_and_wait()
# sender.goback_n()
sender.selective_repeat()