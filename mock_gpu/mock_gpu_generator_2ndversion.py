import smtplib
import time
import json
import random
from datetime import datetime
import sqlite3
import os
from email.mime.text import MIMEText
from collections import defaultdict
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
NUM_GPUS = random.randint(1, 4)
INTERVAL = 5
LOG_FILE = "mock_gpu_log.json"
DB_FILE = "mock_gpu_log.db"
EMAIL_ALERT_ENABLED = False

# Email settings
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_RECEIVER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # Use app-specific password

# Plotting config
MAX_POINTS = 20
PLOT_DELAY = 2  # how many intervals before plotting starts
gpu_plot_data = defaultdict(lambda: {"time": [], "temp": [], "util": [], "mem": []})

# Initialize matplotlib
plt.ion()
plt.figure(figsize=(12, 6))

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS gpu_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gpu_index INTEGER,
            timestamp TEXT,
            gpu_utilization INTEGER,
            memory_used_MB INTEGER,
            memory_total_MB INTEGER,
            temperature_C INTEGER,
            power_usage_W REAL,
            fan_speed_percent INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gpu_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gpu_id INTEGER,
            pid INTEGER,
            name TEXT,
            used_memory_MB INTEGER,
            FOREIGN KEY (gpu_id) REFERENCES gpu_stats(id)
        )
    """)
    conn.commit()
    conn.close()

# --- LOGGING ---
def save_to_db(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for entry in data:
        c.execute("""
            INSERT INTO gpu_stats (gpu_index, timestamp, gpu_utilization, memory_used_MB,
                                   memory_total_MB, temperature_C, power_usage_W, fan_speed_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["gpu_index"], entry["timestamp"], entry["gpu_utilization"], entry["memory_used_MB"],
            entry["memory_total_MB"], entry["temperature_C"], entry["power_usage_W"], entry["fan_speed_percent"]
        ))
        gpu_id = c.lastrowid
        for proc in entry.get("processes", []):
            c.execute("INSERT INTO gpu_processes (gpu_id, pid, name, used_memory_MB) VALUES (?, ?, ?, ?)",
                      (gpu_id, proc["pid"], proc["name"], proc["used_memory_MB"]))
    conn.commit()
    conn.close()

def save_to_json(data, filename=LOG_FILE):
    with open(filename, "a") as f:
        for entry in data:
            json.dump(entry, f)
            f.write("\n")

# --- EMAIL ALERT ---
def send_email_alert(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("✅ Email alert sent.")
    except Exception as e:
        print("❌ Email alert failed:", e)

# --- MONITORING ---
def generate_mock_gpu_stats(num_gpus):
    data = []
    mock_processes = [
        {"name": "python.exe", "mem": 1200},
        {"name": "blender.exe", "mem": 2500},
        {"name": "stable_diffusion.py", "mem": 6000},
        {"name": "ollama", "mem": 4500}
    ]
    for i in range(num_gpus):
        total_memory = 16384 if i % 2 == 0 else 24576
        used_memory = random.randint(int(total_memory * 0.2), int(total_memory * 0.9))
        utilization = random.randint(30, 95)
        temp = random.randint(55, 88)
        power = random.uniform(120.0, 350.0)
        fan_speed = int(max(20, min(100, (temp - 30) * 1.5)))

        active_processes = []
        if random.random() > 0.3:
            for _ in range(random.randint(1, 2)):
                proc = random.choice(mock_processes)
                active_processes.append({
                    "pid": random.randint(1000, 20000),
                    "name": proc["name"],
                    "used_memory_MB": random.randint(proc["mem"] - 500, proc["mem"] + 500)
                })

        gpu_info = {
            "gpu_index": i,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gpu_utilization": utilization,
            "memory_used_MB": used_memory,
            "memory_total_MB": total_memory,
            "temperature_C": temp,
            "power_usage_W": power,
            "fan_speed_percent": fan_speed,
            "processes": active_processes
        }

        # Alerting
        if temp >= 80:
            print("🚨 Temperature alert triggered!")
            if EMAIL_ALERT_ENABLED:
                send_email_alert(
                    subject="🔥 GPU Temperature Alert",
                    body=(
                        f"GPU {i} temperature is {temp}°C\n"
                        f"Utilization: {utilization}%\n"
                        f"Memory: {used_memory}/{total_memory} MB\n"
                        f"Time: {gpu_info['timestamp']}"
                    )
                )

        data.append(gpu_info)
    return data

def print_status(entry):
    print("=" * 60)
    print(f"[{entry['timestamp']}] GPU {entry['gpu_index']}")
    print(f"Utilization: {entry['gpu_utilization']}%")
    print(f"Memory: {entry['memory_used_MB']}/{entry['memory_total_MB']} MB")
    print(f"Temperature: {entry['temperature_C']}°C")
    print(f"Fan Speed: {entry['fan_speed_percent']}%")
    print(f"Power Usage: {entry['power_usage_W']:.2f} W")
    if entry["processes"]:
        print("Active Processes:")
        for p in entry["processes"]:
            print(f" - PID {p['pid']} | {p['name']} | {p['used_memory_MB']} MB")
    else:
        print("No active mock processes.")
    print("=" * 60)

def update_plot():
    plt.clf()
    for gpu_id, data in sorted(gpu_plot_data.items()):
        times = data["time"]
        plt.subplot(NUM_GPUS, 1, gpu_id + 1)
        plt.plot(times, data["temp"], label="Temp (°C)", color="red")
        plt.plot(times, data["util"], label="Util (%)", color="blue")
        plt.plot(times, data["mem"], label="Mem (MB)", color="green")
        plt.title(f"GPU {gpu_id}")
        plt.ylabel("Value")
        plt.xticks(rotation=45)
        plt.legend(loc="upper left")
        plt.tight_layout()
    plt.pause(0.01)

# --- MAIN LOOP ---
if __name__ == "__main__":
    print(f"🟢 Mock GPU data generator started for {NUM_GPUS} GPUs. Press Ctrl+C to stop.")
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    if os.path.exists(DB_FILE): os.remove(DB_FILE)

    init_db()
    cycle = 0

    try:
        while True:
            stats = generate_mock_gpu_stats(NUM_GPUS)
            save_to_json(stats)
            save_to_db(stats)

            for entry in stats:
                print_status(entry)

                # Update plot data
                gpu_id = entry["gpu_index"]
                ts = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                gpu_plot_data[gpu_id]["time"].append(ts)
                gpu_plot_data[gpu_id]["temp"].append(entry["temperature_C"])
                gpu_plot_data[gpu_id]["util"].append(entry["gpu_utilization"])
                gpu_plot_data[gpu_id]["mem"].append(entry["memory_used_MB"])

                # Trim
                for key in ["time", "temp", "util", "mem"]:
                    if len(gpu_plot_data[gpu_id][key]) > MAX_POINTS:
                        gpu_plot_data[gpu_id][key].pop(0)

            cycle += 1
            if cycle >= PLOT_DELAY:
                update_plot()
            else:
                print(f"⏳ Waiting for data... ({cycle}/{PLOT_DELAY})")

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")
        plt.ioff()
        plt.show()
