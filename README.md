# CA‑GPU‑Monitoring 🖥️

**A simple Python tool for monitoring GPU statistics** such as utilization, temperature, memory usage, and more :contentReference[oaicite:1]{index=1}.

---

## 🔍 Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Supported Backends](#supported-backends)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## 📌 Features
- Real-time monitoring of:
  - GPU utilization
  - Temperature
  - Memory usage
  - Fan speed (where available)
- Lightweight and easy-to-use
- Supports both real and mock GPU data (useful for testing)
- Modular backend architecture (e.g., NVIDIA’s DCGM)

---

## ⚙️ Requirements
- Python 3.7+
- Working GPU with appropriate drivers (for production usage)
- Recommended:
  - `nvidia-driver`, `nvidia-smi`, or DCGM for NVIDIA GPUs
  - Modules: `pynvml`, `pydcgm`, etc.

---

## 🚀 Installation

Use `pip` to install:

```bash
pip install ca-gpu-monitoring

