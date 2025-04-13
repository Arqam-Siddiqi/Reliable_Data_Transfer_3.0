import time
import random
from network import Network
from rdt_3_0 import Rdt3Sender, Rdt3Receiver
from gbn import GbnSender, GbnReceiver
from sr import SrSender, SrReceiver

def generate_data(count, size):
    """Generate random data packets"""
    data = []
    for i in range(count):
        packet_data = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=size))
        data.append(f"Data-{i}-{packet_data}")
    return data

def test_rdt3():
    print("\n\n\n===== Testing RDT 3.0 (Stop-and-Wait) =====\n\n")
    network = Network(loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2)
    sender = Rdt3Sender(network, timeout=0.5, max_attempts=5)
    receiver = Rdt3Receiver(network)
    
    # Generate test data
    data = generate_data(5, 10)
    received_data = []
    
    # Send each packet and receive
    for i, packet_data in enumerate(data):
        print(f"\nSending packet {i}: {packet_data}")
        
        # Start receiver in a separate thread so it can receive while sender is sending
        import threading
        received = [None]  # Use a list to store the result from the thread
        receiver_done = threading.Event()
        
        def receive_thread():
            try:
                received[0] = receiver.receive()
                print(f"Received: {received[0]}")
                receiver_done.set()
            except Exception as e:
                print(f"Receiver thread error: {e}")
                receiver_done.set()
        
        thread = threading.Thread(target=receive_thread)
        thread.daemon = True
        thread.start()
        
        # Now send the packet (with timeout handling)
        send_result = sender.send(packet_data)
        
        # Wait for receiver to finish or timeout
        receiver_done.wait(timeout=2.0)
        
        if received[0] is not None:
            received_data.append(received[0])
        else:
            print("Error: Failed to receive packet")
    
    # Verify all data was received correctly
    success = len(data) == len(received_data) and all(d == r for d, r in zip(data, received_data))
    print(f"\nAll packets transmitted successfully: {success}")
    
    network.shutdown()
    return success

def test_gbn():
    print("\n\n\n===== Testing Go-Back-N =====\n\n")
    network = Network(loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2)
    sender = GbnSender(network, window_size=4, timeout=0.5)
    receiver = GbnReceiver(network)
    
    # Generate test data
    data = generate_data(10, 10)
    print(f"Sending data: {data}")
    
    # Start receiver in separate thread
    import threading
    receiver_done = threading.Event()
    
    def receive_thread():
        try:
            receiver.receive(len(data))
            receiver_done.set()
        except Exception as e:
            print(f"Receiver thread error: {e}")
            receiver_done.set()
    
    receiver_thread = threading.Thread(target=receive_thread)
    receiver_thread.daemon = True
    receiver_thread.start()
    
    # Send all packets
    send_result = sender.send(data)
    
    # Wait for receiver to finish or timeout
    receiver_done.wait(timeout=10.0)
    
    # Verify all data was received correctly
    received_data = receiver.received_data
    print(f"Received data: {received_data}")
    success = len(data) == len(received_data) and all(d == r for d, r in zip(data, received_data))
    print(f"\nAll packets transmitted successfully: {success}")
    
    network.shutdown()
    return success

def test_sr():
    print("\n\n\n===== Testing Selective Repeat =====\n\n")
    network = Network(loss_prob=0.2, corrupt_prob=0.2, delay_prob=0.2)
    sender = SrSender(network, window_size=4, timeout=0.5)
    receiver = SrReceiver(network, window_size=4)
    
    # Generate test data
    data = generate_data(10, 10)
    print(f"Sending data: {data}")
    
    # Start receiver in separate thread
    import threading
    receiver_done = threading.Event()
    
    def receive_thread():
        try:
            receiver.receive(len(data))
            receiver_done.set()
        except Exception as e:
            print(f"Receiver thread error: {e}")
            receiver_done.set()
    
    receiver_thread = threading.Thread(target=receive_thread)
    receiver_thread.daemon = True
    receiver_thread.start()
    
    # Send all packets
    send_result = sender.send(data)
    
    # Wait for receiver to finish or timeout
    receiver_done.wait(timeout=10.0)
    
    # Verify all data was received correctly
    received_data = receiver.received_data
    print(f"Received data: {received_data}")
    success = len(data) == len(received_data) and all(d == r for d, r in zip(data, received_data))
    print(f"\nAll packets transmitted successfully: {success}")
    
    network.shutdown()
    return success

if __name__ == "__main__":
    print("Starting RDT Protocol Testing")
    
    rdt3_success = test_rdt3()
    time.sleep(1)
    
    gbn_success = test_gbn()
    time.sleep(1)
    
    sr_success = test_sr()
    
    # Print summary
    print("\n===== Test Summary =====")
    print(f"RDT 3.0 (Stop-and-Wait): {'Passed' if rdt3_success else 'Failed'}")
    print(f"Go-Back-N: {'Passed' if gbn_success else 'Failed'}")
    print(f"Selective Repeat: {'Passed' if sr_success else 'Failed'}")