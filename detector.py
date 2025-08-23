# detector.py
import time
from collections import defaultdict
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

# simple in-memory flow windower
WINDOW = 10.0  # seconds
flows = defaultdict(lambda: {'count':0, 'bytes':0, 'first':None, 'last':None, 'ports':set()})

def add_packet(record):
    ts, src, dst, proto, length = record
    key = src  # detect per source IP (you can use 5-tuple)
    f = flows[key]
    if f['first'] is None:
        f['first'] = ts
    f['last'] = ts
    f['count'] += 1
    f['bytes'] += length
    # you can store dest port if TCP/UDP - skipped here

def extract_features_and_flush(now=None):
    if now is None:
        now = time.time()
    to_delete = []
    X = []
    ips = []
    for ip, f in list(flows.items()):
        if f['last'] and now - f['last'] > WINDOW:
            duration = (f['last'] - f['first']) if f['first'] else 0.001
            pkt_rate = f['count'] / max(duration, 0.001)
            avg_pkt_size = f['bytes'] / max(f['count'],1)
            feature = [f['count'], f['bytes'], pkt_rate, avg_pkt_size, len(f['ports'])]
            X.append(feature)
            ips.append(ip)
            to_delete.append(ip)
    for ip in to_delete:
        del flows[ip]
    return np.array(X), ips

# load or train a model (train on small synthetic benign flows)
def bootstrap_model():
    try:
        clf = joblib.load("iforest.joblib")
        return clf
    except:
        # train a trivial model on synthetic "normal" data
        normal = np.random.poisson(lam=5, size=(200,1))
        normal_bytes = np.random.normal(500,200,(200,1)).clip(1)
        pkt_rate = np.random.normal(1,0.5,(200,1)).clip(0.01)
        avg_size = normal_bytes/normal
        ports = np.random.randint(1,4,(200,1))
        X = np.hstack([normal, normal_bytes, pkt_rate, avg_size, ports])
        clf = IsolationForest(contamination=0.02, random_state=0)
        clf.fit(X)
        joblib.dump(clf, "iforest.joblib")
        return clf

clf = bootstrap_model()
