# webui.py
from flask import Flask, jsonify, request
import sqlite3, subprocess

app = Flask(__name__)
DB = "alerts.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, ip TEXT, score REAL, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()
init_db()

@app.route("/alerts")
def alerts():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, ip, score, ts FROM alerts ORDER BY ts DESC LIMIT 200")
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

@app.route("/block", methods=["POST"])
def block():
    ip = request.json.get("ip")
    reason = request.json.get("reason", "manual")
    cmd = ["powershell", "-Command", f"New-NetFirewallRule -DisplayName 'ManualBlock_{ip}' -Direction Inbound -RemoteAddress {ip} -Action Block -Description '{reason}'"]
    subprocess.run(cmd)
    return jsonify({"status":"ok", "ip":ip})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
