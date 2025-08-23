# capture_agent.py
# lightweight packet capture agent for the PoC
import threading
import queue
from scapy.all import sniff, IP

# shared queue used by main.py
q = queue.Queue()

def pkt_handler(pkt):
    """called by scapy for each sniffed packet"""
    try:
        if IP in pkt:
            ts = pkt.time
            src = pkt[IP].src
            dst = pkt[IP].dst
            proto = pkt[IP].proto
            length = len(pkt)
            q.put((ts, src, dst, proto, length))
    except Exception:
        # don't let exceptions kill the sniffer thread
        import traceback
        traceback.print_exc()

def capture(iface=None):
    """blocking sniff loop (runs in a thread)"""
    # iface=None -> scapy picks default interface; set iface="Ethernet" or GUID if needed
    sniff(iface=iface, prn=pkt_handler, store=False)

def start_capture(iface=None):
    """start capture() in a daemon thread and return the Thread object"""
    t = threading.Thread(target=capture, kwargs={'iface': iface}, daemon=True)
    t.start()
    return t

if __name__ == "__main__":
    # run standalone for quick debugging: prints queue items
    print("Starting capture (standalone). Press Ctrl+C to stop.")
    start_capture(iface=None)
    try:
        while True:
            try:
                item = q.get(timeout=5)
                print("got", item)
            except queue.Empty:
                print(".", end="", flush=True)
    except KeyboardInterrupt:
        print("\nexiting.")
