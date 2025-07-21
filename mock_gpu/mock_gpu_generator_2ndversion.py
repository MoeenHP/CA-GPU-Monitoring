import time
import json
import random
from datetime import datetime
import sqlite3
import os

# --- CONFIGURATION ---
NUM_GPUS = 4  # ⚙️ تعداد کارت‌های گرافیک مصنوعی که میخواهید شبیه‌سازی کنید
INTERVAL = 5  # ثانیه: فاصله زمانی بین هر بار تولید لاگ
LOG_FILE = "mock_gpu_log.json"
DB_FILE = "mock_gpu_log.db"


# --- توابع کپی شده از اسکریپت اصلی شما برای سازگاری کامل ---

def init_db():
    """پایگاه داده و جداول را در صورت عدم وجود ایجاد می‌کند."""
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
            fan_speed_percent INTEGER -- ✅ تغییر ۱: ستون سرعت فن اضافه شد
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


def save_to_db(data):
    """داده‌های مصنوعی را در پایگاه داده SQLite ذخیره می‌کند."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for entry in data:
        # ✅ تغییر ۲: ستون و مقدار سرعت فن به کوئری INSERT اضافه شد
        c.execute("""
            INSERT INTO gpu_stats (gpu_index, timestamp, gpu_utilization, memory_used_MB, memory_total_MB, temperature_C, power_usage_W, fan_speed_percent)
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
    """داده‌های مصنوعی را در فایل JSON ذخیره می‌کند."""
    with open(filename, "a") as f:
        for entry in data:
            json.dump(entry, f)
            f.write("\n")


def print_status(entry):
    """وضعیت یک GPU مصنوعی را در ترمینال چاپ می‌کند."""
    print("=" * 60)
    print(f" شبیه‌سازی [MOCK] [{entry['timestamp']}] GPU {entry['gpu_index']}")
    print(f"Utilization: {entry['gpu_utilization']}%")
    print(f"Memory: {entry['memory_used_MB']}/{entry['memory_total_MB']} MB")
    print(f"Temperature: {entry['temperature_C']}°C")
    print(f"Fan Speed: {entry['fan_speed_percent']}%")  # ✅ تغییر ۳: نمایش سرعت فن اضافه شد
    print(f"Power Usage: {entry['power_usage_W']:.2f} W")
    processes = entry.get("processes", [])
    if processes:
        print("Active Mock Processes:")
        for p in processes:
            print(f" - PID {p['pid']} | {p['name']} | {p['used_memory_MB']} MB")
    else:
        print("No active mock processes.")
    print("=" * 60)


# --- تابع اصلی برای تولید داده مصنوعی ---

def generate_mock_gpu_stats(num_gpus):
    """
    برای تعداد مشخصی GPU، داده‌های آماری مصنوعی و واقع‌گرایانه تولید می‌کند.
    """
    data = []
    mock_processes = [
        {"name": "python.exe", "mem": 1200},
        {"name": "blender.exe", "mem": 2500},
        {"name": "stable_diffusion.py", "mem": 6000},
        {"name": "ollama", "mem": 4500}
    ]

    for i in range(num_gpus):
        if i % 2 == 0:
            total_memory = 16384
        else:
            total_memory = 24576

        used_memory = random.randint(int(total_memory * 0.2), int(total_memory * 0.9))
        utilization = random.randint(30, 95)
        temp = random.randint(55, 88)
        power = random.uniform(120.0, 350.0)

        # ✅ تغییر ۴: تولید داده برای سرعت فن بر اساس دما
        fan_speed = int(max(20, min(100, (temp - 30) * 1.5)))

        active_processes = []
        if random.random() > 0.3:
            num_procs = random.randint(1, 2)
            for _ in range(num_procs):
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
            "fan_speed_percent": fan_speed,  # و افزودن آن به دیکشنری خروجی
            "processes": active_processes
        }
        data.append(gpu_info)

    return data


if __name__ == "__main__":
    print(f"🟢 Mock GPU data generator started for {NUM_GPUS} GPUs. Press Ctrl+C to stop.")

    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    init_db()

    try:
        while True:
            mock_stats = generate_mock_gpu_stats(NUM_GPUS)

            save_to_json(mock_stats)
            save_to_db(mock_stats)

            print(f"\n--- Cycle at {datetime.now().strftime('%H:%M:%S')} ---")
            for entry in mock_stats:
                print_status(entry)

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped by user.")
