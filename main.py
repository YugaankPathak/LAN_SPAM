# main_debug.py
import time
import subprocess
import queue as _queue
import sqlite3
import traceback

# import capture queue + helper to start capture
from capture_agent import q, start_capture    # ensure capture_agent.py exposes start_capture()
from detector import add_packet, extract_features_and_flush, clf

ALERT_THRESHOLD = -0.70  # adjust if you want fewer alerts
FLUSH_INTERVAL = 5.0
WHITELIST = [
    "192.168.29.1",   # gateway
    "192.168.29.61",  # laptop (example)
    "10.20.160.1",    # other trusted device
]

def block_ip_windows(ip, reason="Detected spam"):
    cmd = [
        "powershell",
        "-Command",
        f"New-NetFirewallRule -DisplayName 'Block_{ip}' -Direction Inbound -RemoteAddress {ip} -Action Block -Description '{reason}'"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("block command finished. returncode:", res.returncode)
        print("stdout:", res.stdout.strip())
        print("stderr:", res.stderr.strip())
    except Exception as e:
        print("Exception when running block command:", e)
        traceback.print_exc()

def ensure_capture_started():
    try:
        print("Starting capture thread (iface=None)...")
        start_capture(iface=None)  # None = scapy picks the default; change if needed
    except Exception as e:
        print("Failed to start capture thread:", e)
        traceback.print_exc()

def mainloop():
    print("IsolationForest clf:", type(clf), "ready")
    ensure_capture_started()
    last_flush = time.time()
    last_any_record = time.time()

    try:
        while True:
            try:
                record = q.get(timeout=1)
                last_any_record = time.time()
                print("got record from q:", record)
                add_packet(record)
            except _queue.Empty:
                # print a heartbeat dot so you see the program is alive
                print(".", end="", flush=True)

            if time.time() - last_flush > FLUSH_INTERVAL:
                print("\nflushing flows...")
                X, ips = extract_features_and_flush(now=time.time())
                print("extracted", len(ips), "flows")
                if len(ips):
                    try:
                        scores = clf.score_samples(X)
                    except Exception as e:
                        print("Error scoring samples:", e)
                        traceback.print_exc()
                        scores = []
                    for ip, s in zip(ips, scores):
                        print("ip", ip, "score", s)
                        if s < ALERT_THRESHOLD and ip not in WHITELIST:
                            print("ALERT anomalous ip", ip, "score", s)
                            # example: insert into sqlite alerts DB (optional)
                            try:
                                conn = sqlite3.connect("alerts.db")
                                conn.execute("CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, ip TEXT, score REAL, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
                                conn.execute("INSERT INTO alerts (ip, score) VALUES (?, ?)", (ip, float(s)))
                                conn.commit()
                                conn.close()
                            except Exception as e:
                                print("Failed to write alert to DB:", e)
                            block_ip_windows(ip, reason=f"Anomaly score {s:.2f}")
                else:
                    print("no flows to score")
                last_flush = time.time()

            # optional: detect if nothing ever comes in
            if time.time() - last_any_record > 30:
                print("\n[notice] no packets seen for 30s. If you expect traffic, check Npcap / interface.")
                last_any_record = time.time()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt, exiting cleanly.")
    except Exception as e:
        print("Unhandled exception in mainloop:", e)
        traceback.print_exc()

if __name__ == "__main__":
    mainloop()
