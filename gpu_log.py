import time
import json
import pynvml
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import matplotlib.pyplot as plt
import os
import sqlite3

# CONFIGURATION
INTERVAL = 30  # seconds
TEMP_THRESHOLD = 80  # Celsius
LOG_FILE = "gpu_log.json"
DB_FILE = "gpu_log.db"
EMAIL_ALERT_ENABLED = False  # Set to True if you want email alerts

# EMAIL CONFIG (optional)
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_RECEIVER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # App-specific password, not normal one

# Initialize NVML
pynvml.nvmlInit()

# Data cache for live plotting
gpu_data = {}

# Initialize SQLite DB and tables if they don't exist
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

# Save to DB (along with JSON)
def save_to_db(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    for entry in data:
        # Insert into gpu_stats
        c.execute("""
            INSERT INTO gpu_stats (gpu_index, timestamp, gpu_utilization, memory_used_MB, memory_total_MB,
                                  temperature_C, power_usage_W, fan_speed_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["gpu_index"],
            entry["timestamp"],
            entry["gpu_utilization"],
            entry["memory_used_MB"],
            entry["memory_total_MB"],
            entry["temperature_C"],
            entry["power_usage_W"],
            entry["fan_speed_percent"]
        ))
        gpu_id = c.lastrowid

        # Insert related processes
        for proc in entry.get("processes", []):
            c.execute("""
                INSERT INTO gpu_processes (gpu_id, pid, name, used_memory_MB)
                VALUES (?, ?, ?, ?)
            """, (
                gpu_id,
                proc["pid"],
                proc["name"],
                proc["used_memory_MB"]
            ))

    conn.commit()
    conn.close()

def send_email_alert(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("📧 Email alert sent!")
    except Exception as e:
        print("❌ Email alert failed:", e)

def print_status(entry):
    print("=" * 60)
    print(f"[{entry['timestamp']}] GPU {entry['gpu_index']}")
    print(f"Utilization: {entry['gpu_utilization']}%")
    print(f"Memory: {entry['memory_used_MB']}/{entry['memory_total_MB']} MB")
    print(f"Temperature: {entry['temperature_C']}°C")
    print(f"Fan Speed: {entry['fan_speed_percent']}%")
    print(f"Power Usage: {entry['power_usage_W']} W")

    processes = entry.get("processes", [])
    if processes:
        print("Active Processes:")
        for p in processes:
            print(f" - PID {p['pid']} | {p['name']} | {p['used_memory_MB']} MB")
    else:
        print("No active GPU processes.")
    print("=" * 60)

def get_gpu_stats():
    data = []
    device_count = pynvml.nvmlDeviceGetCount()
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
        fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)

        # Get running processes on GPU
        process_info_list = []
        try:
            procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
            for proc in procs:
                pid = proc.pid
                used_mem = proc.usedGpuMemory
                if used_mem is None:
                    used_mem = 0
                else:
                    used_mem = used_mem // 1024 ** 2
                try:
                    import psutil
                    name = psutil.Process(pid).name()
                except:
                    name = "Unknown"
                process_info_list.append({
                    "pid": pid,
                    "name": name,
                    "used_memory_MB": used_mem
                })
        except pynvml.NVMLError:
            process_info_list = []

        gpu_info = {
            "gpu_index": i,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gpu_utilization": util.gpu,
            "memory_used_MB": mem.used // 1024**2,
            "memory_total_MB": mem.total // 1024**2,
            "temperature_C": temp,
            "power_usage_W": power,
            "fan_speed_percent": fan_speed,
            "processes": process_info_list  # ✅ Added
        }

        data.append(gpu_info)

    return data

def save_to_json(data, filename=LOG_FILE):
    with open(filename, "a") as f:
        for entry in data:
            json.dump(entry, f)
            f.write("\n")

def update_plot():
    plt.clf()
    num_gpus = len(gpu_data)

    for idx, (gpu_id, data) in enumerate(gpu_data.items()):
        times = data["time"]
        temp = data["temp"]
        util = data["util"]
        mem = data["mem"]

        plt.subplot(num_gpus, 1, idx + 1)
        plt.plot(times, temp, label="Temp (°C)", color='r')
        plt.plot(times, util, label="Util (%)", color='b')
        plt.plot(times, mem, label="Mem (MB)", color='g')
        plt.title(f"GPU {gpu_id}")
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.xticks(rotation=45)
        plt.legend(loc="upper left")
        plt.tight_layout()

    plt.pause(0.05)  # Allow plot to update


if __name__ == "__main__":
    print("🟢 GPU Monitoring + Live Plotting started. Press Ctrl+C to stop.")

    init_db()  # Initialize database

    plt.ion()
    plt.figure(figsize=(10, 5))

    try:
        while True:
            stats = get_gpu_stats()
            save_to_json(stats)
            save_to_db(stats)  # Save into SQLite DB

            for entry in stats:
                print_status(entry)
                gpu_id = entry["gpu_index"]

                # Initialize GPU data
                if gpu_id not in gpu_data:
                    gpu_data[gpu_id] = {
                        "time": [],
                        "temp": [],
                        "util": [],
                        "mem": []
                    }

                # Append new sample
                timestamp = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                gpu_data[gpu_id]["time"].append(timestamp)
                gpu_data[gpu_id]["temp"].append(entry["temperature_C"])
                gpu_data[gpu_id]["util"].append(entry["gpu_utilization"])
                gpu_data[gpu_id]["mem"].append(entry["memory_used_MB"])

                # Keep only the last 20 samples
                for key in ["time", "temp", "util", "mem"]:
                    if len(gpu_data[gpu_id][key]) > 20:
                        gpu_data[gpu_id][key].pop(0)

            update_plot()
            time.sleep(INTERVAL)  # Wait only after first plot

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")
        plt.ioff()
        plt.show()
